import io
import json
from datetime import timedelta
from unittest.mock import patch
from urllib.error import URLError

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Product


class ProductUpdateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name="Pen", description="Blue ink", price="12000.00", quantity=30
        )
        self.payload = {
            "name": "Notebook",
            "description": "Lined pages",
            "price": "15000.50",
            "quantity": 12,
        }

    def put(self, product_id=None, payload=None, authorized=True):
        product_id = self.product.pk if product_id is None else product_id
        payload = self.payload if payload is None else payload
        headers = {"HTTP_AUTHORIZATION": "Bearer access-token"} if authorized else {}
        return self.client.put(f"/products/{product_id}", payload, format="json", **headers)

    @staticmethod
    def auth_response():
        response = io.BytesIO(json.dumps({
            "user_id": "u-1", "email": "u@example.com", "role": 0
        }).encode())
        response.status = 200
        return response

    @patch("products.authentication.urlopen")
    def test_put_replaces_fields_and_preserves_id_created_at(self, urlopen):
        urlopen.side_effect = lambda *args, **kwargs: self.auth_response()
        old_time = timezone.now() - timedelta(days=1)
        Product.objects.filter(pk=self.product.pk).update(
            created_at=old_time, updated_at=old_time
        )
        self.product.refresh_from_db()

        response = self.put()
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], self.product.pk)
        self.assertEqual(payload["name"], "Notebook")
        self.assertEqual(payload["description"], "Lined pages")
        self.assertEqual(payload["price"], "15000.50")
        self.assertEqual(payload["quantity"], 12)

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Notebook")
        self.assertEqual(self.product.description, "Lined pages")
        self.assertEqual(str(self.product.price), "15000.50")
        self.assertEqual(self.product.quantity, 12)
        self.assertEqual(self.product.created_at, old_time)
        self.assertGreater(self.product.updated_at, old_time)

    @patch("products.authentication.urlopen")
    def test_missing_or_forbidden_fields_return_400_without_update(self, urlopen):
        urlopen.side_effect = lambda *args, **kwargs: self.auth_response()
        missing = self.payload.copy()
        del missing["quantity"]
        response = self.put(payload=missing)
        self.assertEqual(response.status_code, 400)
        self.assertIn("quantity", response.json())

        with_id = {**self.payload, "id": 999}
        response = self.put(payload=with_id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("id", response.json())
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Pen")

    @patch("products.authentication.urlopen")
    def test_missing_and_invalid_id_do_not_create(self, urlopen):
        urlopen.side_effect = lambda *args, **kwargs: self.auth_response()
        self.assertEqual(self.put(999).status_code, 404)
        for product_id in ("abc", "0", "-1", "1.5"):
            with self.subTest(product_id=product_id):
                self.assertEqual(self.put(product_id).status_code, 400)
        self.assertEqual(Product.objects.count(), 1)

    @patch("products.authentication.urlopen")
    def test_missing_token_and_unavailable_auth_do_not_update(self, urlopen):
        self.assertEqual(self.put(authorized=False).status_code, 401)
        urlopen.assert_not_called()
        urlopen.side_effect = URLError("connection refused")
        self.assertEqual(self.put().status_code, 503)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Pen")

    @patch("products.authentication.urlopen")
    def test_authentication_precedes_id_validation(self, urlopen):
        self.assertEqual(self.put("bad", authorized=False).status_code, 401)
        urlopen.assert_not_called()
