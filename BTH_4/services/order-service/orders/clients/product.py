"""Read product snapshots and check stock without mutating Product Service."""

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from orders.clients.http import open_service
from orders.errors import OrderAPIError


MAX_SQLITE_INTEGER = 9223372036854775807
MAX_PRICE = Decimal("99999999.99")


@dataclass(frozen=True)
class ProductSnapshot:
    id: int
    name: str
    price: Decimal
    quantity: int


def _unavailable():
    return OrderAPIError(503, "product_unavailable", "Product service is unavailable.")


def _parse_snapshot(payload, product_id):
    if not isinstance(payload, dict):
        raise _unavailable()
    identifier = payload.get("id")
    name = payload.get("name")
    price_raw = payload.get("price")
    quantity = payload.get("quantity")
    if (
        type(identifier) is not int
        or identifier != product_id
        or not 0 < identifier <= MAX_SQLITE_INTEGER
        or not isinstance(name, str)
        or not name.strip()
        or len(name) > 255
        or not isinstance(price_raw, str)
        or not price_raw.strip()
        or type(quantity) is not int
        or not 0 <= quantity <= MAX_SQLITE_INTEGER
    ):
        raise _unavailable()
    try:
        price = Decimal(price_raw)
    except InvalidOperation as exc:
        raise _unavailable() from exc
    if (
        not price.is_finite()
        or price < 0
        or price > MAX_PRICE
        or price.as_tuple().exponent < -2
    ):
        raise _unavailable()
    return ProductSnapshot(identifier, name, price.quantize(Decimal("0.01")), quantity)


def get_product(product_id, token):
    request = Request(
        f"{settings.PRODUCT_SERVICE_URL.rstrip('/')}/products/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with open_service(request, timeout=settings.PRODUCT_SERVICE_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise _unavailable()
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 401:
            raise AuthenticationFailed("Invalid or expired token.") from exc
        if exc.code == 404:
            raise OrderAPIError(
                400, "product_not_found", "Product does not exist.", product_id=product_id
            ) from exc
        raise _unavailable() from exc
    except (URLError, TimeoutError, OSError, ValueError, UnicodeError, HTTPException) as exc:
        raise _unavailable() from exc
    return _parse_snapshot(payload, product_id)


def ensure_stock(product, requested_quantity):
    if requested_quantity > product.quantity:
        raise OrderAPIError(
            409,
            "insufficient_stock",
            "Requested quantity exceeds available stock.",
            product_id=product.id,
            requested_quantity=requested_quantity,
            available_quantity=product.quantity,
        )
