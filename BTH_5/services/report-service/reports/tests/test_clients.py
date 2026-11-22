"""Unit tests for Product Service and Order Service HTTP clients."""
import io
import json
from decimal import Decimal
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase
from rest_framework.exceptions import AuthenticationFailed

from reports.clients.http import NoRedirectHandler
from reports.clients.order import get_order, list_order_items, list_orders
from reports.clients.product import get_product, list_products
from reports.errors import ReportAPIError


def _response(payload, status=200):
    buf = io.BytesIO(json.dumps(payload).encode())
    buf.status = status
    return buf


class ClientTests(SimpleTestCase):
    def test_no_redirect_handler_drops_redirects(self):
        handler = NoRedirectHandler()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "http://evil/"))

    def test_list_products_parses_and_sorts(self):
        payload = [
            {"id": 2, "name": "Book", "price": "5.00", "quantity": 10},
            {"id": 1, "name": "Pen", "price": "10.25", "quantity": 50},
        ]
        with patch("reports.clients.product.open_service", return_value=_response(payload)):
            products = list_products("tok")
        self.assertEqual([p.id for p in products], [1, 2])
        self.assertEqual(products[0].price, Decimal("10.25"))
        self.assertEqual(products[0].quantity, 50)

    def test_product_client_handles_errors_and_malformed_data(self):
        with patch(
            "reports.clients.product.open_service",
            side_effect=HTTPError("http://p/products/1", 404, "Not Found", {}, None),
        ):
            self.assertIsNone(get_product(1, "tok", allow_missing=True))
            with self.assertRaises(ReportAPIError) as ctx:
                get_product(1, "tok", missing_status=400)
            self.assertEqual(ctx.exception.status_code, 400)

        with patch(
            "reports.clients.product.open_service",
            side_effect=HTTPError("http://p/products", 401, "Unauthorized", {}, None),
        ):
            with self.assertRaises(AuthenticationFailed):
                list_products("tok")

        for bad in ({"not": "list"}, [{"id": 1, "name": "A", "price": "-1.00", "quantity": 1}]):
            with patch("reports.clients.product.open_service", return_value=_response(bad)):
                with self.assertRaises(ReportAPIError) as ctx:
                    list_products("tok")
                self.assertEqual(ctx.exception.status_code, 503)

    def test_order_client_parses_orders_items_and_detail(self):
        orders_payload = [
            {
                "id": 2,
                "customer_name": "Bob",
                "customer_email": "bob@example.com",
                "total_amount": "25.00",
                "status": "completed",
                "created_at": "2026-11-20T10:00:00Z",
                "updated_at": "2026-11-20T11:00:00Z",
            }
        ]
        items_payload = [
            {
                "id": 5,
                "order_id": 2,
                "product_id": 1,
                "product_name": "Pen",
                "quantity": 2,
                "unit_price": "12.50",
                "total_price": "25.00",
            }
        ]
        with patch("reports.clients.order.open_service", return_value=_response(orders_payload)):
            orders = list_orders("tok")
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].total_amount, Decimal("25.00"))

        with patch("reports.clients.order.open_service", return_value=_response(items_payload)):
            items = list_order_items("tok")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].total_price, Decimal("25.00"))

        detail_payload = dict(orders_payload[0], items=items_payload)
        with patch("reports.clients.order.open_service", return_value=_response(detail_payload)):
            detail = get_order(2, "tok")
        self.assertEqual(len(detail.items), 1)

    def test_order_client_handles_unavailable_and_404(self):
        with patch("reports.clients.order.open_service", side_effect=URLError("down")):
            with self.assertRaises(ReportAPIError) as ctx:
                list_orders("tok")
            self.assertEqual(ctx.exception.status_code, 503)

        with patch(
            "reports.clients.order.open_service",
            side_effect=HTTPError("http://o/orders/99", 404, "Not Found", {}, None),
        ):
            with self.assertRaises(ReportAPIError) as ctx:
                get_order(99, "tok")
            self.assertEqual(ctx.exception.status_code, 404)
