import io
import json
from unittest.mock import patch
from urllib.error import URLError

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Product


class DeleteProductTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name="Pen", description="Blue ink", price="12000.00", quantity=30
        )

    def delete(self, product_id=None, authorized=True):
        product_id = self.product.pk if product_id is None else product_id
        headers = {"HTTP_AUTHORIZATION": "Bearer access-token"} if authorized else {}
        return self.client.delete(f"/products/{product_id}", **headers)

    @patch("products.authentication.urlopen")
    def test_delete_removes_product_and_returns_empty_204(self, urlopen):
        urlopen.side_effect = lambda *args, **kwargs: self.auth_response()

        response = self.delete()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

        repeated = self.delete()
        self.assertEqual(repeated.status_code, 404)
        self.assertEqual(repeated.json()["detail"], "Product not found.")
        self.assertEqual(urlopen.call_count, 2)

    @patch("products.authentication.urlopen")
    def test_missing_and_invalid_ids(self, urlopen):
        urlopen.side_effect = lambda *args, **kwargs: self.auth_response()
        self.assertEqual(self.delete(999).status_code, 404)
        for product_id in ("abc", "0", "-1", "1.5"):
            with self.subTest(product_id=product_id):
                self.assertEqual(self.delete(product_id).status_code, 400)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    @patch("products.authentication.urlopen")
    def test_missing_token_and_auth_failure_do_not_delete(self, urlopen):
        response = self.delete(authorized=False)
        self.assertEqual(response.status_code, 401)
        urlopen.assert_not_called()

        urlopen.side_effect = URLError("connection refused")
        response = self.delete()
        self.assertEqual(response.status_code, 503)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    @patch("products.authentication.urlopen")
    def test_authentication_precedes_id_validation(self, urlopen):
        self.assertEqual(self.delete("bad", authorized=False).status_code, 401)
        urlopen.assert_not_called()

    @staticmethod
    def auth_response():
        response = io.BytesIO(json.dumps({
            "user_id": "u-1", "email": "u@example.com", "role": 0
        }).encode())
        response.status = 200
        return response
