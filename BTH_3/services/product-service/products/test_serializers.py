from django.test import TestCase

from products.models import Product
from products.serializers import ProductSerializer


class ProductSerializerTests(TestCase):
    def payload(self, **changes):
        data = {
            "name": "  Bút bi  ",
            "description": "  Mực xanh  ",
            "price": "12000.00",
            "quantity": 30,
        }
        data.update(changes)
        return data

    def test_create_trims_and_renders_decimal_and_timestamps(self):
        serializer = ProductSerializer(data=self.payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()
        output = ProductSerializer(Product.objects.get(pk=product.pk)).data
        self.assertEqual(output["name"], "Bút bi")
        self.assertEqual(output["description"], "Mực xanh")
        self.assertEqual(output["price"], "12000.00")
        self.assertEqual(output["quantity"], 30)
        self.assertEqual(output["id"], product.pk)
        self.assertTrue(output["created_at"].endswith("Z"))
        self.assertTrue(output["updated_at"].endswith("Z"))

    def test_price_and_quantity_boundaries_and_duplicate_names(self):
        for price in ("0", "99999999.99"):
            with self.subTest(price=price):
                serializer = ProductSerializer(data=self.payload(name="Same", price=price, quantity=0))
                self.assertTrue(serializer.is_valid(), serializer.errors)
                serializer.save()
        self.assertEqual(Product.objects.filter(name="Same").count(), 2)
        self.assertEqual(ProductSerializer(Product.objects.order_by("id").first()).data["price"], "0.00")

    def test_put_requires_all_writable_fields(self):
        creator = ProductSerializer(data=self.payload())
        self.assertTrue(creator.is_valid(), creator.errors)
        product = creator.save()
        for missing in ("name", "description", "price", "quantity"):
            with self.subTest(missing=missing):
                data = self.payload()
                del data[missing]
                serializer = ProductSerializer(product, data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn(missing, serializer.errors)

    def test_full_update_changes_writable_fields_only(self):
        creator = ProductSerializer(data=self.payload())
        self.assertTrue(creator.is_valid(), creator.errors)
        product = creator.save()
        old_id, old_created_at = product.pk, product.created_at
        updater = ProductSerializer(
            product,
            data=self.payload(name="New", description="Updated", price="0.50", quantity=0),
        )
        self.assertTrue(updater.is_valid(), updater.errors)
        updated = updater.save()
        self.assertEqual(updated.pk, old_id)
        self.assertEqual(updated.created_at, old_created_at)
        self.assertEqual(updated.name, "New")
        self.assertEqual(ProductSerializer(updated).data["price"], "0.50")

    def test_invalid_text_and_price(self):
        cases = (
            ("name", " \t "),
            ("description", "  "),
            ("name", "x" * 256),
            ("name", 123),
            ("description", True),
            ("price", "-0.01"),
            ("price", "100000000.00"),
            ("price", "1.001"),
            ("price", "abc"),
            ("price", False),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                serializer = ProductSerializer(data=self.payload(**{field: value}))
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_invalid_quantity_types_and_values(self):
        for value in (-1, True, False, 1.0, 1.2, "1", "1.2", None):
            with self.subTest(value=value):
                serializer = ProductSerializer(data=self.payload(quantity=value))
                self.assertFalse(serializer.is_valid())
                self.assertIn("quantity", serializer.errors)

    def test_missing_fields_rejected_for_create(self):
        for missing in ("name", "description", "price", "quantity"):
            with self.subTest(missing=missing):
                data = self.payload()
                del data[missing]
                serializer = ProductSerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn(missing, serializer.errors)

    def test_unknown_and_read_only_fields_rejected_on_create_and_update(self):
        creator = ProductSerializer(data=self.payload())
        self.assertTrue(creator.is_valid(), creator.errors)
        product = creator.save()
        for field, value in (("other", 1), ("id", 99), ("created_at", "2026-01-01T00:00:00Z"), ("updated_at", "2026-01-01T00:00:00Z")):
            with self.subTest(field=field):
                for instance in (None, product):
                    serializer = ProductSerializer(instance, data=self.payload(**{field: value}))
                    self.assertFalse(serializer.is_valid())
                    self.assertIn(field, serializer.errors)
