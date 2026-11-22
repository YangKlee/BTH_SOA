import io
import json
from dataclasses import FrozenInstanceError
from decimal import Decimal
from http.client import IncompleteRead
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed

from orders.clients.product import ProductSnapshot, ensure_stock, get_product
from orders.errors import OrderAPIError


class FakeHTTPResponse(io.BytesIO):
    status = 200


@override_settings(
    PRODUCT_SERVICE_URL="http://product.example:8001/",
    PRODUCT_SERVICE_TIMEOUT_SECONDS=2.75,
)
class ProductClientTests(SimpleTestCase):
    def setUp(self):
        self.product = {"id": 17, "name": "Blue pen", "price": "12000.50", "quantity": 5}

    @patch("orders.clients.product.open_service")
    def test_fetch_uses_get_bearer_timeout_and_returns_immutable_decimal_snapshot(self, transport):
        transport.return_value = FakeHTTPResponse(json.dumps(self.product).encode())
        product = get_product(17, "access-token")
        self.assertEqual(product, ProductSnapshot(17, "Blue pen", Decimal("12000.50"), 5))
        with self.assertRaises(FrozenInstanceError):
            product.quantity = 100
        sent = transport.call_args.args[0]
        self.assertEqual(sent.full_url, "http://product.example:8001/products/17")
        self.assertEqual(sent.get_method(), "GET")
        self.assertEqual(sent.get_header("Authorization"), "Bearer access-token")
        self.assertEqual(transport.call_args.kwargs, {"timeout": 2.75})
        transport.assert_called_once()

    @patch("orders.clients.product.open_service")
    def test_zero_price_and_zero_inventory_are_valid_snapshots(self, transport):
        transport.return_value = FakeHTTPResponse(json.dumps(
            self.product | {"price": "0.00", "quantity": 0}
        ).encode())
        product = get_product(17, "access-token")
        self.assertEqual(product.price, Decimal("0.00"))
        self.assertEqual(product.quantity, 0)

    @patch("orders.clients.product.open_service")
    def test_missing_product_is_400_with_numeric_product_id(self, transport):
        transport.side_effect = HTTPError("http://product.example", 404, "Not found", {}, None)
        with self.assertRaises(OrderAPIError) as caught:
            get_product(17, "access-token")
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.detail["code"], "product_not_found")
        self.assertEqual(caught.exception.detail["product_id"], 17)

    @patch("orders.clients.product.open_service")
    def test_upstream_token_rejection_stays_401(self, transport):
        transport.side_effect = HTTPError("http://product.example", 401, "Unauthorized", {}, None)
        with self.assertRaises(AuthenticationFailed):
            get_product(17, "expired-token")

    @patch("orders.clients.product.open_service")
    def test_network_timeout_server_and_redirect_errors_are_503(self, transport):
        errors = [TimeoutError(), URLError("connection refused"), OSError(), IncompleteRead(b"", 10)]
        errors += [HTTPError("http://product.example", status, "upstream error", {}, None)
                   for status in (301, 302, 403, 400, 500, 503)]
        for error in errors:
            with self.subTest(error=repr(error)):
                transport.side_effect = error
                with self.assertRaises(OrderAPIError) as caught:
                    get_product(17, "access-token")
                self.assertEqual(caught.exception.status_code, 503)
                self.assertEqual(caught.exception.detail["code"], "product_unavailable")

    @patch("orders.clients.product.open_service")
    def test_malformed_json_and_product_fields_are_503(self, transport):
        bodies = [b"not json", b"\xff", b"null", b"[]", b"{}"]
        invalid_fields = {
            "id": (18, True, "17", 0),
            "name": (None, "", " ", 42, "x" * 256),
            "price": (None, True, 12.0, "", "NaN", "Infinity", "-0.01", "bad",
                      "1.001", "100000000.00"),
            "quantity": (True, -1, 2.5, "5", None, 9223372036854775808),
        }
        for field, values in invalid_fields.items():
            for value in values:
                bodies.append(json.dumps(self.product | {field: value}).encode())
        for field in self.product:
            bodies.append(json.dumps({key: value for key, value in self.product.items() if key != field}).encode())
        for body in bodies:
            with self.subTest(body=body):
                transport.return_value = FakeHTTPResponse(body)
                with self.assertRaises(OrderAPIError) as caught:
                    get_product(17, "access-token")
                self.assertEqual(caught.exception.status_code, 503)

    @patch("orders.clients.product.open_service")
    def test_non_200_success_status_is_rejected(self, transport):
        response = FakeHTTPResponse(b"{}")
        response.status = 204
        transport.return_value = response
        with self.assertRaises(OrderAPIError) as caught:
            get_product(17, "access-token")
        self.assertEqual(caught.exception.status_code, 503)

    def test_sufficient_stock_including_exact_available_quantity(self):
        product = ProductSnapshot(17, "Pen", Decimal("3.00"), 5)
        self.assertIsNone(ensure_stock(product, 1))
        self.assertIsNone(ensure_stock(product, 5))

    def test_insufficient_stock_preserves_numeric_error_context(self):
        for available, requested in ((5, 6), (0, 1)):
            with self.subTest(available=available):
                product = ProductSnapshot(17, "Pen", Decimal("3.00"), available)
                with self.assertRaises(OrderAPIError) as caught:
                    ensure_stock(product, requested)
                error = caught.exception
                self.assertEqual(error.status_code, 409)
                self.assertEqual(error.detail["code"], "insufficient_stock")
                self.assertEqual(error.detail["product_id"], 17)
                self.assertEqual(error.detail["requested_quantity"], requested)
                self.assertEqual(error.detail["available_quantity"], available)
