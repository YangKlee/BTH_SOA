"""Read orders and order items from Order Service over HTTP."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from reports.clients.http import open_service
from reports.errors import ReportAPIError
from reports.validation import SQLITE_MAX_INTEGER, VALID_ORDER_STATUSES


MAX_ORDER_AMOUNT = Decimal("99999999.99")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class OrderItemSnapshot:
    id: int
    order_id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal


@dataclass(frozen=True)
class OrderSnapshot:
    id: int
    customer_name: str
    customer_email: str
    total_amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
    items: tuple[OrderItemSnapshot, ...] = ()


def _unavailable():
    return ReportAPIError(503, "order_unavailable", "Order service is unavailable.")


def _parse_money(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise _unavailable()
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise _unavailable() from exc
    if (
        not value.is_finite()
        or value < 0
        or value > MAX_ORDER_AMOUNT
        or value.as_tuple().exponent < -2
    ):
        raise _unavailable()
    return value.quantize(CENT)


def _parse_timestamp(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise _unavailable()
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise _unavailable() from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_item(payload, expected_order_id=None):
    if not isinstance(payload, dict):
        raise _unavailable()
    item_id = payload.get("id")
    order_id = payload.get("order_id")
    product_id = payload.get("product_id")
    product_name = payload.get("product_name")
    quantity = payload.get("quantity")
    if (
        type(item_id) is not int
        or not 0 < item_id <= SQLITE_MAX_INTEGER
        or type(order_id) is not int
        or not 0 < order_id <= SQLITE_MAX_INTEGER
        or (expected_order_id is not None and order_id != expected_order_id)
        or type(product_id) is not int
        or not 0 < product_id <= SQLITE_MAX_INTEGER
        or not isinstance(product_name, str)
        or not product_name.strip()
        or len(product_name) > 255
        or type(quantity) is not int
        or not 0 < quantity <= SQLITE_MAX_INTEGER
    ):
        raise _unavailable()
    unit_price = _parse_money(payload.get("unit_price"))
    total_price = _parse_money(payload.get("total_price"))
    return OrderItemSnapshot(
        id=item_id,
        order_id=order_id,
        product_id=product_id,
        product_name=product_name,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
    )


def _parse_order(payload, expected_id=None, *, require_items=False):
    if not isinstance(payload, dict):
        raise _unavailable()
    order_id = payload.get("id")
    customer_name = payload.get("customer_name")
    customer_email = payload.get("customer_email")
    status = payload.get("status")
    if (
        type(order_id) is not int
        or not 0 < order_id <= SQLITE_MAX_INTEGER
        or (expected_id is not None and order_id != expected_id)
        or not isinstance(customer_name, str)
        or not customer_name.strip()
        or len(customer_name) > 255
        or not isinstance(customer_email, str)
        or not customer_email.strip()
        or len(customer_email) > 255
        or status not in VALID_ORDER_STATUSES
    ):
        raise _unavailable()

    total_amount = _parse_money(payload.get("total_amount"))
    created_at = _parse_timestamp(payload.get("created_at"))
    updated_at = _parse_timestamp(payload.get("updated_at"))

    items = ()
    if require_items or "items" in payload:
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise _unavailable()
        parsed_items = [_parse_item(entry, expected_order_id=order_id) for entry in raw_items]
        parsed_items.sort(key=lambda entry: entry.id)
        items = tuple(parsed_items)

    return OrderSnapshot(
        id=order_id,
        customer_name=customer_name,
        customer_email=customer_email,
        total_amount=total_amount,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        items=items,
    )


def _get_json(path, token, *, not_found_error=None):
    request = Request(
        f"{settings.ORDER_SERVICE_URL.rstrip('/')}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with open_service(request, timeout=settings.ORDER_SERVICE_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise _unavailable()
            return json.load(response)
    except HTTPError as exc:
        if exc.code == 401:
            raise AuthenticationFailed("Invalid or expired token.") from exc
        if exc.code == 404 and not_found_error is not None:
            raise not_found_error from exc
        raise _unavailable() from exc
    except (URLError, TimeoutError, OSError, ValueError, UnicodeError, HTTPException) as exc:
        raise _unavailable() from exc


def list_orders(token):
    payload = _get_json("/orders", token)
    if not isinstance(payload, list):
        raise _unavailable()
    seen = set()
    orders = []
    for entry in payload:
        order = _parse_order(entry)
        if order.id in seen:
            raise _unavailable()
        seen.add(order.id)
        orders.append(order)
    orders.sort(key=lambda item: item.id)
    return orders


def list_order_items(token):
    payload = _get_json("/order_items", token)
    if not isinstance(payload, list):
        raise _unavailable()
    seen = set()
    items = []
    for entry in payload:
        item = _parse_item(entry)
        if item.id in seen:
            raise _unavailable()
        seen.add(item.id)
        items.append(item)
    items.sort(key=lambda entry: entry.id)
    return items


def get_order(order_id, token, *, missing_status=404):
    payload = _get_json(
        f"/orders/{order_id}",
        token,
        not_found_error=ReportAPIError(
            missing_status,
            "order_not_found",
            "Order does not exist.",
            order_id=order_id,
        ),
    )
    return _parse_order(payload, expected_id=order_id, require_items=True)
