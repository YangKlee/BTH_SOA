"""Real separate-connection SQLite tests; run with ORDER_TEST_DB set to a file."""

import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

from django.db import connection, connections, transaction
from django.test import TransactionTestCase

from orders import services
from orders.clients.product import ProductSnapshot
from orders.errors import OrderAPIError
from orders.models import Order, OrderItem


def file_database():
    return not connection.is_in_memory_db()


class ConcurrentOrderTests(TransactionTestCase):
    def setUp(self):
        if not file_database():
            self.skipTest("Set ORDER_TEST_DB to a temporary SQLite file for real concurrency tests.")
        self.order = Order.objects.create(customer_name="Concurrency", customer_email="test@example.com", total_amount=Decimal("10.00"))
        self.item = OrderItem.objects.create(order=self.order, product_id=1, product_name="First", quantity=1, unit_price=Decimal("10.00"), total_price=Decimal("10.00"))

    def worker(self, action):
        try:
            return action()
        except OrderAPIError as exc:
            return exc.status_code
        finally:
            connections.close_all()

    def test_simultaneous_duplicate_add_has_one_winner(self):
        barrier = threading.Barrier(2)
        def fetch(product_id, token):
            self.assertFalse(connections["default"].in_atomic_block)
            barrier.wait(timeout=10)
            return ProductSnapshot(product_id, "Second", Decimal("5.00"), 100)
        def add():
            services.add_item({"order_id": self.order.id, "product_id": 2, "quantity": 2}, "token")
            return 201
        with patch("orders.services.get_product", side_effect=fetch):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(self.worker, add) for _ in range(2)]
                statuses = sorted(f.result(timeout=15) for f in futures)
        self.assertEqual(statuses, [201, 409])
        self.order.refresh_from_db()
        self.assertEqual(self.order.items.count(), 2)
        self.assertEqual(self.order.total_amount, Decimal("20.00"))

    def test_simultaneous_different_additions_preserve_total(self):
        barrier = threading.Barrier(2)
        def fetch(product_id, token):
            barrier.wait(timeout=10)
            return ProductSnapshot(product_id, "New", Decimal("7.25"), 100)
        def add(product_id):
            services.add_item({"order_id": self.order.id, "product_id": product_id, "quantity": 2}, "token")
            return 201
        with patch("orders.services.get_product", side_effect=fetch):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(self.worker, lambda p=p: add(p)) for p in (2, 3)]
                self.assertEqual([f.result(timeout=15) for f in futures], [201, 201])
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_amount, Decimal("39.00"))
        self.assertEqual(self.order.items.count(), 3)

    def test_cancel_during_item_network_check_blocks_late_update(self):
        entered, release = threading.Event(), threading.Event()
        def fetch(product_id, token):
            entered.set()
            if not release.wait(timeout=10):
                raise RuntimeError("Timed out waiting for cancellation")
            return ProductSnapshot(product_id, "First", Decimal("10.00"), 100)
        with patch("orders.services.get_product", side_effect=fetch):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.worker, lambda: services.update_item(self.item.id, 3, "token"))
                try:
                    self.assertTrue(entered.wait(timeout=10))
                    services.change_order_status(self.order.id, "cancelled", "token")
                finally:
                    release.set()
                self.assertEqual(future.result(timeout=15), 409)
        self.item.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.item.quantity, 1)
        self.assertEqual(self.order.total_amount, Decimal("10.00"))
        self.assertEqual(self.order.status, "cancelled")

    def test_database_lock_timeout_is_controlled_503(self):
        entered, release = threading.Event(), threading.Event()
        def hold_lock():
            with transaction.atomic():
                entered.set()
                if not release.wait(timeout=10):
                    raise RuntimeError("Timed out waiting for busy test")
        with ThreadPoolExecutor(max_workers=1) as executor:
            holder = executor.submit(self.worker, hold_lock)
            try:
                self.assertTrue(entered.wait(timeout=10))
                with self.assertRaises(OrderAPIError) as caught:
                    services.delete_order(self.order.id)
                self.assertEqual(caught.exception.status_code, 503)
                self.assertEqual(caught.exception.detail["code"], "database_busy")
            finally:
                release.set()
            holder.result(timeout=15)
        self.assertTrue(Order.objects.filter(pk=self.order.id).exists())
