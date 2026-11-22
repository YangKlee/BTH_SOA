from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test import TransactionTestCase

from orders import services
from orders.clients.product import ProductSnapshot
from orders.errors import OrderAPIError
from orders.models import Order, OrderItem


class OrderServicesTests(TransactionTestCase):
    def setUp(self):
        self.products = {
            1: ProductSnapshot(1, "Pen", Decimal("12.25"), 100),
            2: ProductSnapshot(2, "Book", Decimal("20.10"), 100),
            3: ProductSnapshot(3, "Free sample", Decimal("0.00"), 100),
        }
        self.remote = patch("orders.services.get_product", side_effect=self.fetch).start()
        self.addCleanup(patch.stopall)

    def fetch(self, product_id, token):
        self.assertFalse(connection.in_atomic_block, "Remote HTTP cannot run inside a DB transaction")
        self.assertEqual(token, "test-access")
        return self.products[product_id]

    def create(self, items=None):
        return services.create_order({
            "customer_name": "Test Customer", "customer_email": "test@example.com",
            "items": items or [{"product_id": 1, "quantity": 2}],
        }, "test-access")

    def assert_error(self, status, call, code=None):
        with self.assertRaises(OrderAPIError) as caught:
            call()
        self.assertEqual(caught.exception.status_code, status)
        if code:
            self.assertEqual(caught.exception.detail["code"], code)

    def test_nested_create_snapshots_and_exact_total(self):
        order = self.create([{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 3}])
        self.assertEqual(order.total_amount, Decimal("84.80"))
        self.assertEqual(order.status, "pending")
        self.assertEqual(list(order.items.values_list("total_price", flat=True)), [Decimal("24.50"), Decimal("60.30")])
        self.assertEqual(order.items.first().product_name, "Pen")

    def test_stock_failure_in_second_line_leaves_no_order(self):
        self.assert_error(409, lambda: self.create([
            {"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 101},
        ]), "insufficient_stock")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_dependency_failure_leaves_no_order(self):
        def fail_late(product_id, token):
            if product_id == 2:
                raise OrderAPIError(503, "product_unavailable", "Unavailable")
            return self.fetch(product_id, token)
        self.remote.side_effect = fail_late
        self.assert_error(503, lambda: self.create([
            {"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 1},
        ]))
        self.assertFalse(Order.objects.exists())

    def test_insert_failure_rolls_back_parent_order(self):
        with patch.object(OrderItem.objects, "bulk_create", side_effect=RuntimeError("injected failure")):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(Order.objects.exists())

    def test_overflow_checked_before_quantization(self):
        self.products[1] = ProductSnapshot(1, "Expensive", Decimal("99999999.99"), 2**63 - 1)
        self.assert_error(400, lambda: self.create([{"product_id": 1, "quantity": 2**63 - 1}]))
        self.assertFalse(Order.objects.exists())

    def test_total_overflow_even_when_each_line_fits(self):
        self.products[1] = ProductSnapshot(1, "A", Decimal("60000000.00"), 10)
        self.products[2] = ProductSnapshot(2, "B", Decimal("60000000.00"), 10)
        self.assert_error(400, lambda: self.create([
            {"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 1},
        ]))
        self.assertFalse(Order.objects.exists())

    def test_add_update_delete_recalculates_and_preserves_snapshots(self):
        order = self.create()
        created_at, initial_updated = order.created_at, order.updated_at
        added = services.add_item({"order_id": order.id, "product_id": 2, "quantity": 2}, "test-access")
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("64.70"))
        self.assertGreater(order.updated_at, initial_updated)
        self.products[2] = ProductSnapshot(2, "Renamed", Decimal("99.00"), 100)
        updated = services.update_item(added.id, 3, "test-access")
        self.assertEqual(updated.unit_price, Decimal("20.10"))
        self.assertEqual(updated.product_name, "Book")
        self.assertEqual(updated.total_price, Decimal("60.30"))
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("84.80"))
        self.assertEqual(order.created_at, created_at)
        self.remote.reset_mock()
        services.delete_item(added.id)
        self.remote.assert_not_called()
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("24.50"))

    def test_add_overflow_rolls_back_item_and_total(self):
        order = self.create()
        self.products[2] = ProductSnapshot(2, "Expensive", Decimal("99999999.99"), 100)
        self.assert_error(400, lambda: services.add_item({"order_id": order.id, "product_id": 2, "quantity": 1}, "test-access"))
        order.refresh_from_db()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_amount, Decimal("24.50"))

    def test_update_overflow_rolls_back_item(self):
        self.products[1] = ProductSnapshot(1, "Expensive", Decimal("60000000.00"), 100)
        order = self.create([{"product_id": 1, "quantity": 1}])
        item = order.items.get()
        self.assert_error(400, lambda: services.update_item(item.id, 2, "test-access"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("60000000.00"))

    def test_last_item_and_duplicate_blocked(self):
        order = self.create()
        self.assert_error(409, lambda: services.delete_item(order.items.get().id), "last_item")
        self.assert_error(409, lambda: services.add_item({"order_id": order.id, "product_id": 1, "quantity": 1}, "test-access"), "duplicate_product")
        self.assertEqual(order.items.count(), 1)

    def test_status_matrix_and_noop_timestamp(self):
        for original in ("pending", "completed", "cancelled"):
            for target in ("pending", "completed", "cancelled"):
                with self.subTest(original=original, target=target):
                    order = self.create()
                    order.status = original
                    order.save(update_fields=["status"])
                    before = order.updated_at
                    self.remote.reset_mock()
                    if original != "pending" and original != target:
                        self.assert_error(409, lambda: services.change_order_status(order.id, target, "test-access"))
                    else:
                        result = services.change_order_status(order.id, target, "test-access")
                        self.assertEqual(result.status, target)
                        if original == target:
                            self.assertEqual(result.updated_at, before)
                            self.remote.assert_not_called()
                        elif target == "completed":
                            self.remote.assert_called_once()
                        else:
                            self.remote.assert_not_called()

    def test_complete_rechecks_stock_and_leaves_pending_on_failure(self):
        order = self.create()
        self.products[1] = ProductSnapshot(1, "Pen", Decimal("100.00"), 1)
        self.assert_error(409, lambda: services.change_order_status(order.id, "completed", "test-access"))
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.total_amount, Decimal("24.50"))

    def test_order_changed_during_remote_checks_is_not_completed(self):
        order = self.create()
        item = order.items.get()
        def change_during_check(product_id, token):
            OrderItem.objects.filter(pk=item.id).update(quantity=3, total_price=Decimal("36.75"))
            Order.objects.filter(pk=order.id).update(total_amount=Decimal("36.75"))
            return self.fetch(product_id, token)
        self.remote.side_effect = change_during_check
        self.assert_error(409, lambda: services.change_order_status(order.id, "completed", "test-access"), "order_changed")
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_terminal_items_blocked_without_product_call(self):
        order = self.create()
        item = order.items.get()
        for status in ("completed", "cancelled"):
            Order.objects.filter(pk=order.id).update(status=status)
            self.remote.reset_mock()
            self.assert_error(409, lambda: services.update_item(item.id, 1, "test-access"))
            self.assert_error(409, lambda: services.delete_item(item.id))
            self.assert_error(409, lambda: services.add_item({"order_id": order.id, "product_id": 2, "quantity": 1}, "test-access"))
            self.remote.assert_not_called()

    def test_delete_order_cascades_without_product(self):
        order = self.create()
        untouched = self.create()
        self.remote.reset_mock()
        services.delete_order(order.id)
        self.remote.assert_not_called()
        self.assertFalse(OrderItem.objects.filter(order_id=order.id).exists())
        self.assertTrue(Order.objects.filter(pk=untouched.id).exists())
        self.assert_error(404, lambda: services.delete_order(order.id))

    def test_zero_price_is_supported(self):
        order = self.create([{"product_id": 3, "quantity": 5}])
        self.assertEqual(order.total_amount, Decimal("0.00"))
