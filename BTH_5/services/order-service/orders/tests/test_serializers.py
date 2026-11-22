from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError

from orders.models import Order, OrderItem
from orders.serializers import (
    ItemCreateSerializer, ItemUpdateSerializer, OrderCreateSerializer,
    OrderDetailSerializer, OrderItemSerializer, OrderListSerializer, OrderStatusSerializer,
)
from orders.validation import SQLITE_MAX_INTEGER, parse_positive_id


class InputSerializerTests(SimpleTestCase):
    def payload(self, **overrides):
        value = {
            "customer_name": "  Nguyen Van A  ", "customer_email": " a@example.com ",
            "items": [{"product_id": 1, "quantity": 2}],
        }
        value.update(overrides)
        return value

    def test_create_accepts_and_trims_valid_payload_without_db(self):
        serializer = OrderCreateSerializer(data=self.payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["customer_name"], "Nguyen Van A")
        self.assertEqual(serializer.validated_data["customer_email"], "a@example.com")

    def test_invalid_text_and_email(self):
        cases = (
            {"customer_name": " "}, {"customer_name": 123}, {"customer_name": "x" * 256},
            {"customer_email": "invalid"}, {"customer_email": False}, {"customer_email": None},
            {"customer_email": "a" * 244 + "@example.com"},
        )
        for change in cases:
            with self.subTest(change=change):
                self.assertFalse(OrderCreateSerializer(data=self.payload(**change)).is_valid())

    def test_rejects_missing_empty_and_duplicate_items(self):
        for items in ([], None, [{"product_id": 1, "quantity": 1}] * 2):
            with self.subTest(items=items):
                self.assertFalse(OrderCreateSerializer(data=self.payload(items=items)).is_valid())
        self.assertFalse(OrderCreateSerializer(data={"customer_name": "A"}).is_valid())

    def test_integer_fields_reject_coercion_and_bounds(self):
        for value in (True, False, 1.0, "1", None, 0, -1, SQLITE_MAX_INTEGER + 1):
            for field in ("product_id", "quantity"):
                item = {"product_id": 1, "quantity": 1, field: value}
                with self.subTest(field=field, value=value):
                    self.assertFalse(OrderCreateSerializer(data=self.payload(items=[item])).is_valid())
        serializer = ItemCreateSerializer(data={"order_id": 1, "product_id": SQLITE_MAX_INTEGER, "quantity": 1})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_readonly_unknown_and_nested_fields_rejected(self):
        for field in ("id", "status", "total_amount", "created_at", "updated_at", "anything"):
            with self.subTest(field=field):
                self.assertFalse(OrderCreateSerializer(data=self.payload(**{field: "x"})).is_valid())
        for field in ("unit_price", "total_price", "product_name", "id", "anything"):
            item = {"product_id": 1, "quantity": 1, field: "x"}
            with self.subTest(nested=field):
                self.assertFalse(OrderCreateSerializer(data=self.payload(items=[item])).is_valid())

    def test_separate_mutation_payloads(self):
        for state in ("pending", "completed", "cancelled"):
            serializer = OrderStatusSerializer(data={"status": state})
            self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(OrderStatusSerializer(data={"status": "shipping"}).is_valid())
        self.assertFalse(OrderStatusSerializer(data={"status": "pending", "customer_name": "X"}).is_valid())
        self.assertTrue(ItemUpdateSerializer(data={"quantity": 3}).is_valid())
        for field in ("order_id", "product_id", "unit_price", "total_price"):
            self.assertFalse(ItemUpdateSerializer(data={"quantity": 1, field: 2}).is_valid())
        self.assertFalse(ItemCreateSerializer(data={"product_id": 1, "quantity": 1}).is_valid())
        self.assertFalse(ItemCreateSerializer(data={"order_id": True, "product_id": 1, "quantity": 1}).is_valid())

    def test_url_id_validation(self):
        self.assertEqual(parse_positive_id("1"), 1)
        self.assertEqual(parse_positive_id(str(SQLITE_MAX_INTEGER)), SQLITE_MAX_INTEGER)
        for raw in ("0", "-1", "1.0", "abc", " 1", "1 ", "١", str(SQLITE_MAX_INTEGER + 1), "9" * 100, None):
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                parse_positive_id(raw)


class ReadSerializerTests(TestCase):
    def test_response_shape_decimal_and_timestamps(self):
        order = Order.objects.create(customer_name="A", customer_email="a@example.com", total_amount=Decimal("2.50"))
        item = OrderItem.objects.create(
            order=order, product_id=3, product_name="Pen", quantity=2,
            unit_price=Decimal("1.25"), total_price=Decimal("2.50"),
        )
        summary = OrderListSerializer(order).data
        self.assertEqual(len(summary), 7)
        self.assertNotIn("items", summary)
        self.assertEqual(summary["total_amount"], "2.50")
        self.assertTrue(summary["created_at"].endswith("Z"))
        detail = OrderDetailSerializer(order).data
        self.assertEqual(detail["items"], [OrderItemSerializer(item).data])
        self.assertEqual(detail["items"][0]["order_id"], order.pk)
        self.assertEqual(detail["items"][0]["unit_price"], "1.25")
        self.assertEqual(len(detail["items"][0]), 7)
