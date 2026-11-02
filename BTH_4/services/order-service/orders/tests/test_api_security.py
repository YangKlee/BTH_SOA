"""Verify the actual ten API operations cannot bypass remote authentication."""

import io
import json
from decimal import Decimal
from unittest.mock import patch
from urllib.error import HTTPError

from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from orders.models import Order, OrderItem


class FakeHTTPResponse(io.BytesIO):
    status = 200


class AllEndpointAuthenticationTests(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.order = Order.objects.create(
            customer_name="Security test",
            customer_email="security@example.com",
            total_amount=Decimal("20.00"),
        )
        self.item = OrderItem.objects.create(
            order=self.order, product_id=1, product_name="First", quantity=1,
            unit_price=Decimal("10.00"), total_price=Decimal("10.00"),
        )
        OrderItem.objects.create(
            order=self.order, product_id=2, product_name="Second", quantity=2,
            unit_price=Decimal("5.00"), total_price=Decimal("10.00"),
        )
        self.endpoints = (
            ("get", "/orders", None),
            ("get", f"/orders/{self.order.id}", None),
            ("post", "/orders", {
                "customer_name": "New customer", "customer_email": "new@example.com",
                "items": [{"product_id": 3, "quantity": 2}],
            }),
            ("put", f"/orders/{self.order.id}", {"status": "completed"}),
            ("delete", f"/orders/{self.order.id}", None),
            ("get", "/order_items", None),
            ("get", f"/order_items/{self.item.id}", None),
            ("post", "/order_items", {
                "order_id": self.order.id, "product_id": 3, "quantity": 2,
            }),
            ("put", f"/order_items/{self.item.id}", {"quantity": 3}),
            ("delete", f"/order_items/{self.item.id}", None),
        )

    def state(self):
        return (
            list(Order.objects.order_by("id").values()),
            list(OrderItem.objects.order_by("id").values()),
        )

    def assert_denied_for_all_operations(self, expected_status):
        initial = self.state()
        with patch("orders.services.get_product") as product:
            for method, url, payload in self.endpoints:
                with self.subTest(method=method, url=url):
                    response = getattr(self.client, method)(url, payload, format="json")
                    self.assertEqual(response.status_code, expected_status)
                    self.assertIn("detail", response.data)
                    if expected_status == 401:
                        self.assertEqual(response["WWW-Authenticate"], "Bearer")
                    self.assertEqual(self.state(), initial)
            product.assert_not_called()

    @patch("orders.authentication.open_service")
    def test_all_ten_operations_reject_missing_token_without_network(self, auth):
        self.assert_denied_for_all_operations(401)
        auth.assert_not_called()

    @patch("orders.authentication.open_service")
    def test_all_ten_operations_reject_malformed_token_without_network(self, auth):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer one two")
        self.assert_denied_for_all_operations(401)
        auth.assert_not_called()

    @patch("orders.authentication.open_service")
    def test_all_ten_operations_reject_expired_token(self, auth):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired-token")
        auth.side_effect = HTTPError("http://auth.example", 401, "Unauthorized", {}, None)
        self.assert_denied_for_all_operations(401)
        self.assertEqual(auth.call_count, 10)

    @patch("orders.authentication.open_service")
    def test_all_ten_operations_fail_closed_when_auth_times_out(self, auth):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer access-token")
        auth.side_effect = TimeoutError("unavailable")
        self.assert_denied_for_all_operations(503)
        self.assertEqual(auth.call_count, 10)

    @patch("orders.authentication.open_service")
    def test_all_ten_operations_fail_closed_for_invalid_auth_response(self, auth):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer access-token")
        auth.side_effect = lambda *a, **kw: FakeHTTPResponse(b'{"user_id":"incomplete"}')
        self.assert_denied_for_all_operations(503)
        self.assertEqual(auth.call_count, 10)


class APITransportPropagationTests(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer access-token")

    @patch("orders.clients.product.open_service")
    @patch("orders.authentication.open_service")
    def test_real_clients_propagate_identity_and_snapshots_outside_db_transactions(self, auth, product):
        def verify_identity(request, *, timeout):
            self.assertFalse(connection.in_atomic_block)
            self.assertEqual(request.get_header("Authorization"), "Bearer access-token")
            self.assertEqual(request.get_method(), "GET")
            self.assertGreater(timeout, 0)
            return FakeHTTPResponse(b'{"user_id":"u-1","email":"u@example.com","role":0}')

        prices = {31: "12.50", 32: "3.00"}

        def fetch_product(request, *, timeout):
            self.assertFalse(connection.in_atomic_block)
            self.assertEqual(request.get_header("Authorization"), "Bearer access-token")
            self.assertEqual(request.get_method(), "GET")
            self.assertGreater(timeout, 0)
            product_id = int(request.full_url.rsplit("/", 1)[1])
            return FakeHTTPResponse(json.dumps({
                "id": product_id, "name": f"Product {product_id}",
                "price": prices[product_id], "quantity": 100,
            }).encode())

        auth.side_effect = verify_identity
        product.side_effect = fetch_product
        created = self.client.post("/orders", {
            "customer_name": "Snapshot test", "customer_email": "snapshot@example.com",
            "items": [{"product_id": 31, "quantity": 2}],
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["total_amount"], "25.00")
        order_id, item_id = created.data["id"], created.data["items"][0]["id"]
        added = self.client.post("/order_items", {
            "order_id": order_id, "product_id": 32, "quantity": 3,
        }, format="json")
        self.assertEqual(added.status_code, 201)
        self.assertEqual(added.data["total_price"], "9.00")

        prices[31] = "99.00"
        updated = self.client.put(f"/order_items/{item_id}", {"quantity": 3}, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["unit_price"], "12.50")
        self.assertEqual(updated.data["total_price"], "37.50")
        completed = self.client.put(f"/orders/{order_id}", {"status": "completed"}, format="json")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.data["status"], "completed")
        self.assertEqual(completed.data["total_amount"], "46.50")
        self.assertEqual(auth.call_count, 4)
        self.assertEqual(product.call_count, 5)

    @patch("orders.clients.product.open_service")
    @patch("orders.authentication.open_service")
    def test_product_401_mid_request_is_401_and_creates_no_partial_order(self, auth, product):
        auth.return_value = FakeHTTPResponse(b'{"user_id":"u-1","email":"u@example.com","role":0}')
        product.side_effect = HTTPError("http://product.example", 401, "Expired", {}, None)
        response = self.client.post("/orders", {
            "customer_name": "Expired test", "customer_email": "expired@example.com",
            "items": [{"product_id": 31, "quantity": 2}],
        }, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
