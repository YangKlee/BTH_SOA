from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from products.models import Product


class ProductDatabaseTests(TestCase):
    def make_product(self, **changes):
        values = {
            "name": "Notebook",
            "description": "A5 ruled",
            "price": Decimal("10.00"),
            "quantity": 0,
        }
        values.update(changes)
        return Product.objects.create(**values)

    def test_table_schema_and_save_read(self):
        product = self.make_product()
        loaded = Product.objects.get(pk=product.pk)
        self.assertEqual(Product._meta.db_table, "products")
        self.assertEqual(loaded.price, Decimal("10.00"))
        self.assertEqual(loaded.quantity, 0)
        self.assertIsInstance(loaded.id, int)
        self.assertIsNotNone(loaded.created_at)
        self.assertIsNotNone(loaded.updated_at)
        self.assertIn("products", connection.introspection.table_names())

    def test_duplicate_names_and_upper_price_boundary(self):
        self.make_product(name="Same", price=Decimal("99999999.99"))
        self.make_product(name="Same", price=Decimal("0.00"))
        self.assertEqual(Product.objects.filter(name="Same").count(), 2)

    def test_db_rejects_negative_values_even_without_model_validation(self):
        product = self.make_product()
        for field in ("price", "quantity"):
            with self.subTest(field=field):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Product.objects.filter(pk=product.pk).update(**{field: -1})

    def test_model_validation_rejects_excess_decimal_digits(self):
        product = Product(
            name="Too expensive",
            description="A5 ruled",
            price=Decimal("100000000.00"),
            quantity=1,
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_created_at_stays_fixed_and_updated_at_changes_on_save(self):
        first = datetime(2026, 1, 1, tzinfo=timezone.utc)
        later = datetime(2026, 1, 2, tzinfo=timezone.utc)
        with patch("django.db.models.fields.timezone.now", return_value=first):
            product = self.make_product()
        with patch("django.db.models.fields.timezone.now", return_value=later):
            product.quantity = 5
            product.save()
        product.refresh_from_db()
        self.assertEqual(product.created_at, first)
        self.assertEqual(product.updated_at, later)
        self.assertEqual(product.quantity, 5)
