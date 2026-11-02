"""Exercise the ten HTTP contracts through routing, auth and real local ORM."""
import io
import json
from decimal import Decimal
from unittest.mock import patch

from rest_framework.test import APITestCase

from orders.clients.product import ProductSnapshot
from orders.errors import OrderAPIError
from orders.models import Order, OrderItem


def auth_response(*args, **kwargs):
    response = io.BytesIO(json.dumps({"user_id": "user-1", "email": "a@example.com", "role": 1}).encode())
    response.status = 200
    return response


class OrderAPITests(APITestCase):
    def setUp(self):
        self.auth_patch = patch("orders.authentication.open_service", side_effect=auth_response)
        self.auth_http = self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)
        self.product_patch = patch("orders.services.get_product", side_effect=self.product)
        self.product_http = self.product_patch.start()
        self.addCleanup(self.product_patch.stop)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer good-access")

    @staticmethod
    def product(product_id, token):
        return ProductSnapshot(product_id, f"Product {product_id}", Decimal("12.50"), 20)

    def payload(self, **overrides):
        values = {"customer_name": "A", "customer_email": "a@example.com", "items": [{"product_id": 1, "quantity": 2}]}
        values.update(overrides)
        return values

    def create(self, **overrides):
        response = self.client.post("/orders", self.payload(**overrides), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def local_order(self, status="pending", products=(1, 2)):
        order = Order.objects.create(customer_name="A", customer_email="a@example.com", status=status)
        for product_id in products:
            OrderItem.objects.create(
                order=order, product_id=product_id, product_name=f"Stored {product_id}", quantity=2,
                unit_price=Decimal("1.25"), total_price=Decimal("2.50"),
            )
        order.total_amount = Decimal("2.50") * len(products)
        order.save(update_fields=["total_amount"])
        return order

    def test_create_nested_order_and_response_contract(self):
        response = self.client.post("/orders", self.payload(items=[{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}]), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response["Location"], f"/orders/{response.data['id']}")
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["total_amount"], "37.50")
        self.assertEqual([i["total_price"] for i in response.data["items"]], ["25.00", "12.50"])
        self.assertEqual([i["product_name"] for i in response.data["items"]], ["Product 1", "Product 2"])
        self.assertEqual(Order.objects.get().total_amount, Decimal("37.50"))
        self.assertEqual(self.product_http.call_count, 2)
        self.assertEqual(self.product_http.call_args.args, (2, "good-access"))

    def test_create_stock_failure_at_later_item_leaves_no_rows(self):
        response = self.client.post("/orders", self.payload(items=[{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 21}]), format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "insufficient_stock")
        self.assertEqual(response.data["product_id"], 2)
        self.assertIs(type(response.data["available_quantity"]), int)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())

    def test_create_validation_rejects_empty_duplicate_and_forged_totals(self):
        for payload in (
            self.payload(items=[]), self.payload(total_amount="0.01"), self.payload(status="completed"),
            self.payload(items=[{"product_id": 1, "quantity": 1}] * 2),
            self.payload(items=[{"product_id": 1, "quantity": 1, "unit_price": "0.01"}]),
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/orders", payload, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())
        self.product_http.assert_not_called()

    def test_create_dependency_error_and_overflow_do_not_write(self):
        self.product_http.side_effect = OrderAPIError(503, "product_unavailable", "Unavailable")
        self.assertEqual(self.client.post("/orders", self.payload(), format="json").status_code, 503)
        self.product_http.side_effect = lambda pid, token: ProductSnapshot(pid, "Expensive", Decimal("99999999.99"), 10)
        self.assertEqual(self.client.post("/orders", self.payload(), format="json").status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_read_lists_empty_and_sorts_orders(self):
        self.assertEqual(self.client.get("/orders").data, [])
        self.assertEqual(self.client.get("/order_items").data, [])
        first = self.local_order()
        second = self.local_order(status="cancelled")
        data = self.client.get("/orders").data
        self.assertEqual([order["id"] for order in data], [first.pk, second.pk])
        self.assertNotIn("items", data[0])

    def test_read_detail_and_items_keep_snapshots_without_product_http(self):
        order = self.local_order()
        self.product_http.side_effect = AssertionError("GET must not call Product")
        response = self.client.get(f"/orders/{order.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_amount"], "5.00")
        self.assertEqual([i["product_name"] for i in response.data["items"]], ["Stored 1", "Stored 2"])
        items = self.client.get("/order_items").data
        self.assertEqual([i["id"] for i in items], list(order.items.values_list("id", flat=True)))
        item = self.client.get(f"/order_items/{items[0]['id']}")
        self.assertEqual(item.status_code, 200)
        self.assertEqual(item.data["unit_price"], "1.25")
        self.product_http.assert_not_called()

    def test_detail_invalid_and_missing_ids(self):
        for collection in ("orders", "order_items"):
            for identifier in ("0", "-1", "abc", "1.5", "9223372036854775808"):
                with self.subTest(collection=collection, identifier=identifier):
                    self.assertEqual(self.client.get(f"/{collection}/{identifier}").status_code, 400)
            self.assertEqual(self.client.get(f"/{collection}/999").status_code, 404)

    def test_status_transition_matrix_and_noop(self):
        for source in ("pending", "completed", "cancelled"):
            for target in ("pending", "completed", "cancelled"):
                with self.subTest(source=source, target=target):
                    order = self.local_order(status=source)
                    before = order.updated_at
                    self.product_http.reset_mock()
                    response = self.client.put(f"/orders/{order.pk}", {"status": target}, format="json")
                    expected = 200 if source == target or source == "pending" else 409
                    self.assertEqual(response.status_code, expected, response.data)
                    order.refresh_from_db()
                    self.assertEqual(order.status, target if expected == 200 else source)
                    self.assertEqual(order.total_amount, Decimal("5.00"))
                    if source == target:
                        self.assertEqual(order.updated_at, before)
                        self.product_http.assert_not_called()
                    elif source == "pending" and target == "completed":
                        self.assertEqual(self.product_http.call_count, 2)
                    else:
                        self.product_http.assert_not_called()

    def test_complete_missing_stock_keeps_pending(self):
        order = self.local_order()
        self.product_http.side_effect = lambda pid, token: ProductSnapshot(pid, "New name", Decimal("100.00"), 0)
        response = self.client.put(f"/orders/{order.pk}", {"status": "completed"}, format="json")
        self.assertEqual(response.status_code, 409)
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.items.first().unit_price, Decimal("1.25"))

    def test_status_rejects_extra_fields_and_invalid_status(self):
        order = self.local_order()
        for data in ({"status": "shipping"}, {"status": "completed", "total_amount": "1.00"}, {}):
            with self.subTest(data=data):
                self.assertEqual(self.client.put(f"/orders/{order.pk}", data, format="json").status_code, 400)

    def test_delete_all_order_states_cascades_and_returns_empty_body(self):
        other = self.local_order()
        self.product_http.side_effect = AssertionError("DELETE must not call Product")
        for state in ("pending", "completed", "cancelled"):
            order = self.local_order(status=state)
            item_ids = list(order.items.values_list("id", flat=True))
            response = self.client.delete(f"/orders/{order.pk}")
            self.assertEqual(response.status_code, 204)
            self.assertEqual(response.content, b"")
            self.assertFalse(OrderItem.objects.filter(pk__in=item_ids).exists())
            self.assertEqual(self.client.delete(f"/orders/{order.pk}").status_code, 404)
        self.assertTrue(Order.objects.filter(pk=other.pk).exists())
        self.product_http.assert_not_called()

    def test_add_item_updates_parent_and_uses_server_snapshot(self):
        order = self.local_order(products=(1,))
        before = order.updated_at
        response = self.client.post("/order_items", {"order_id": order.pk, "product_id": 2, "quantity": 3}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response["Location"], f"/order_items/{response.data['id']}")
        self.assertEqual(response.data["product_name"], "Product 2")
        self.assertEqual(response.data["total_price"], "37.50")
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("40.00"))
        self.assertGreater(order.updated_at, before)

    def test_add_missing_order_duplicate_and_terminal_order(self):
        response = self.client.post("/order_items", {"order_id": 999, "product_id": 2, "quantity": 1}, format="json")
        self.assertEqual(response.status_code, 404)
        order = self.local_order(products=(1,))
        self.assertEqual(self.client.post("/order_items", {"order_id": order.pk, "product_id": 1, "quantity": 1}, format="json").status_code, 409)
        for state in ("completed", "cancelled"):
            order.status = state
            order.save(update_fields=["status"])
            self.assertEqual(self.client.post("/order_items", {"order_id": order.pk, "product_id": 2, "quantity": 1}, format="json").status_code, 409)
        self.product_http.assert_not_called()

    def test_add_insufficient_stock_leaves_original_total(self):
        order = self.local_order(products=(1,))
        response = self.client.post("/order_items", {"order_id": order.pk, "product_id": 2, "quantity": 21}, format="json")
        self.assertEqual(response.status_code, 409)
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("2.50"))
        self.assertEqual(order.items.count(), 1)

    def test_update_quantity_uses_saved_price_and_name(self):
        order = self.local_order(products=(1,))
        item = order.items.get()
        for quantity in (5, 1):
            response = self.client.put(f"/order_items/{item.pk}", {"quantity": quantity}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["product_name"], "Stored 1")
            self.assertEqual(response.data["unit_price"], "1.25")
            self.assertEqual(response.data["total_price"], f"{Decimal('1.25') * quantity:.2f}")
            order.refresh_from_db()
            self.assertEqual(order.total_amount, Decimal("1.25") * quantity)

    def test_update_rejects_bad_payload_missing_item_and_lack_of_stock(self):
        order = self.local_order(products=(1,))
        item = order.items.get()
        for data in ({"quantity": 0}, {"quantity": True}, {"quantity": "1"}, {"quantity": 1, "product_id": 2}, {"quantity": 1, "unit_price": "0.01"}):
            with self.subTest(data=data):
                self.assertEqual(self.client.put(f"/order_items/{item.pk}", data, format="json").status_code, 400)
        self.assertEqual(self.client.put("/order_items/999", {"quantity": 1}, format="json").status_code, 404)
        self.assertEqual(self.client.put(f"/order_items/{item.pk}", {"quantity": 21}, format="json").status_code, 409)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

    def test_delete_item_recalculates_total_without_product_http(self):
        order = self.local_order()
        first, second = list(order.items.all())
        self.product_http.side_effect = AssertionError("DELETE must not call Product")
        response = self.client.delete(f"/order_items/{first.pk}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("2.50"))
        self.assertEqual(self.client.delete(f"/order_items/{second.pk}").status_code, 409)
        self.assertTrue(OrderItem.objects.filter(pk=second.pk).exists())
        self.assertEqual(self.client.delete(f"/order_items/{first.pk}").status_code, 404)
        self.product_http.assert_not_called()

    def test_terminal_orders_prevent_item_update_and_delete(self):
        for state in ("completed", "cancelled"):
            order = self.local_order(status=state)
            item = order.items.first()
            self.assertEqual(self.client.put(f"/order_items/{item.pk}", {"quantity": 1}, format="json").status_code, 409)
            self.assertEqual(self.client.delete(f"/order_items/{item.pk}").status_code, 409)
        self.product_http.assert_not_called()

    def test_all_ten_endpoints_require_access_token(self):
        order = self.local_order()
        item = order.items.first()
        self.client.credentials()
        cases = (
            ("get", "/orders", None), ("get", f"/orders/{order.pk}", None),
            ("post", "/orders", self.payload()), ("put", f"/orders/{order.pk}", {"status": "cancelled"}),
            ("delete", f"/orders/{order.pk}", None), ("get", "/order_items", None),
            ("get", f"/order_items/{item.pk}", None),
            ("post", "/order_items", {"order_id": order.pk, "product_id": 3, "quantity": 1}),
            ("put", f"/order_items/{item.pk}", {"quantity": 1}),
            ("delete", f"/order_items/{item.pk}", None),
        )
        for method, path, body in cases:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path, body, format="json")
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["WWW-Authenticate"], "Bearer")
        self.assertEqual(order.items.count(), 2)
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())

    def test_unsupported_methods_and_trailing_slash(self):
        order = self.local_order()
        for path in ("/orders", f"/orders/{order.pk}", "/order_items", f"/order_items/{order.items.first().pk}"):
            self.assertEqual(self.client.patch(path, {}, format="json").status_code, 405)
        self.assertEqual(self.client.get("/orders/").status_code, 404)

    def test_full_lifecycle_through_all_ten_routes(self):
        order = self.create()
        added = self.client.post("/order_items", {"order_id": order["id"], "product_id": 2, "quantity": 1}, format="json")
        self.assertEqual(added.status_code, 201)
        item_id = added.data["id"]
        self.assertEqual(self.client.get("/orders").status_code, 200)
        self.assertEqual(self.client.get(f"/orders/{order['id']}").data["total_amount"], "37.50")
        self.assertEqual(self.client.get("/order_items").status_code, 200)
        self.assertEqual(self.client.get(f"/order_items/{item_id}").status_code, 200)
        self.assertEqual(self.client.put(f"/order_items/{item_id}", {"quantity": 2}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/order_items/{item_id}").status_code, 204)
        completed = self.client.put(f"/orders/{order['id']}", {"status": "completed"}, format="json")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.data["total_amount"], "25.00")
        self.assertEqual(self.client.delete(f"/orders/{order['id']}").status_code, 204)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
