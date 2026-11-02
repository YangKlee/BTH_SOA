import io
import json
from unittest.mock import patch
from urllib.error import URLError

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Product


class ProductDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name="Pen", description="Blue ink", price="12000.00", quantity=30
        )

    def get(self, product_id=None, authorized=True):
        product_id = self.product.pk if product_id is None else product_id
        headers = {"HTTP_AUTHORIZATION": "Bearer access-token"} if authorized else {}
        return self.client.get(f"/products/{product_id}", **headers)

    @staticmethod
    def auth_response():
        response = io.BytesIO(json.dumps({
            "user_id": "u-1", "email": "u@example.com", "role": 0
        }).encode())
        response.status = 200
        return response

    @patch("products.authentication.urlopen")
    def test_existing_product_returns_complete_representation(self, urlopen):
        urlopen.side_effect = lambda *args, **kwargs: self.auth_response()
        response = self.get()
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {
            "id", "name", "description", "price", "quantity", "created_at", "updated_at"
        })
        self.assertEqual(payload["id"], self.product.pk)
        self.assertEqual(payload["name"], "Pen")
        self.assertEqual(payload["description"], "Blue ink")
        self.assertEqual(payload["price"], "12000.00")
        self.assertEqual(payload["quantity"], 30)
        self.assertTrue(payload["created_at"])
        self.assertTrue(payload["updated_at"])
        urlopen.assert_called_once()

    @patch("products.authentication.urlopen")
    def test_missing_and_invalid_id(self, urlopen):
        urlopen.side_effect = lambda *args, **kwargs: self.auth_response()
        self.assertEqual(self.get(999).status_code, 404)
        for product_id in ("abc", "0", "-1", "1.5", "99999999999999999999"):
            with self.subTest(product_id=product_id):
                response = self.get(product_id)
                self.assertEqual(response.status_code, 400)
                self.assertIn("detail", response.json())

    @patch("products.authentication.urlopen")
    def test_missing_token_and_unavailable_auth(self, urlopen):
        response = self.get(authorized=False)
        self.assertEqual(response.status_code, 401)
        urlopen.assert_not_called()

        urlopen.side_effect = URLError("connection refused")
        response = self.get()
        self.assertEqual(response.status_code, 503)

    @patch("products.authentication.urlopen")
    def test_authentication_precedes_id_validation(self, urlopen):
        self.assertEqual(self.get("abc", authorized=False).status_code, 401)
        urlopen.assert_not_called()
