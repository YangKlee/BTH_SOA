"""Read product catalog snapshots from Product Service over HTTP."""

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from reports.clients.http import open_service
from reports.errors import ReportAPIError
from reports.validation import SQLITE_MAX_INTEGER


MAX_PRICE = Decimal("99999999.99")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class ProductSnapshot:
    id: int
    name: str
    price: Decimal
    quantity: int


def _unavailable():
    return ReportAPIError(503, "product_unavailable", "Product service is unavailable.")


def _parse_product(payload, expected_id=None):
    if not isinstance(payload, dict):
        raise _unavailable()
    identifier = payload.get("id")
    name = payload.get("name")
    price_raw = payload.get("price")
    quantity = payload.get("quantity")
    if (
        type(identifier) is not int
        or (expected_id is not None and identifier != expected_id)
        or not 0 < identifier <= SQLITE_MAX_INTEGER
        or not isinstance(name, str)
        or not name.strip()
        or len(name) > 255
        or not isinstance(price_raw, str)
        or not price_raw.strip()
        or type(quantity) is not int
        or not 0 <= quantity <= SQLITE_MAX_INTEGER
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
    return ProductSnapshot(identifier, name, price.quantize(CENT), quantity)


def list_products(token):
    request = Request(
        f"{settings.PRODUCT_SERVICE_URL.rstrip('/')}/products",
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
        raise _unavailable() from exc
    except (URLError, TimeoutError, OSError, ValueError, UnicodeError, HTTPException) as exc:
        raise _unavailable() from exc

    if not isinstance(payload, list):
        raise _unavailable()

    seen = set()
    products = []
    for entry in payload:
        product = _parse_product(entry)
        if product.id in seen:
            raise _unavailable()
        seen.add(product.id)
        products.append(product)
    products.sort(key=lambda item: item.id)
    return products


def get_product(product_id, token, *, allow_missing=False, missing_status=400):
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
            if allow_missing:
                return None
            raise ReportAPIError(
                missing_status,
                "product_not_found",
                "Product does not exist.",
                product_id=product_id,
            ) from exc
        raise _unavailable() from exc
    except (URLError, TimeoutError, OSError, ValueError, UnicodeError, HTTPException) as exc:
        raise _unavailable() from exc

    return _parse_product(payload, expected_id=product_id)
