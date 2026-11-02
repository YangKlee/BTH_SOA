from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from orders.models import Order, OrderItem


class OrderModelTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(customer_name="A", customer_email="a@example.com")

    def item(self, **overrides):
        values = dict(
            order=self.order, product_id=1, product_name="Pen", quantity=2,
            unit_price=Decimal("1.25"), total_price=Decimal("2.50"),
        )
        values.update(overrides)
        return OrderItem.objects.create(**values)

    def test_defaults_and_cascade_leave_other_orders_intact(self):
        self.assertEqual(self.order.status, "pending")
        self.assertEqual(self.order.total_amount, Decimal("0.00"))
        self.assertIsNotNone(self.order.created_at.tzinfo)
        item = self.item()
        other = Order.objects.create(customer_name="B", customer_email="b@example.com")
        other_item = self.item(order=other)
        self.order.delete()
        self.assertFalse(OrderItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(OrderItem.objects.filter(pk=other_item.pk).exists())

    def test_invalid_order_values_are_rejected_by_database(self):
        for values in ({"total_amount": Decimal("-0.01")}, {"status": "unknown"}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                Order.objects.create(customer_name="X", customer_email="x@example.com", **values)

    def test_invalid_item_values_are_rejected_by_database(self):
        for values in (
            {"product_id": 0}, {"quantity": 0}, {"quantity": -1},
            {"unit_price": Decimal("-0.01")}, {"total_price": Decimal("-0.01")},
        ):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                self.item(**values)

    def test_product_unique_only_within_order(self):
        self.item()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.item()
        other = Order.objects.create(customer_name="B", customer_email="b@example.com")
        self.item(order=other)
        self.assertEqual(OrderItem.objects.count(), 2)

    def test_product_id_is_not_a_foreign_key(self):
        field = OrderItem._meta.get_field("product_id")
        self.assertFalse(field.is_relation)
        self.assertEqual(OrderItem._meta.get_field("order").column, "order_id")
