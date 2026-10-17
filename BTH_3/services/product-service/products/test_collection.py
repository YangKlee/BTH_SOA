import io
import json
from decimal import Decimal
from unittest.mock import patch
from urllib.error import URLError

from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Product


class FakeHTTPResponse(io.BytesIO):
    status = 200


class ProductCollectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def authenticated_get(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer access-token")
        payload = {"user_id": "u-1", "email": "u@example.com", "role": 0}
        with patch("products.authentication.urlopen", return_value=FakeHTTPResponse(json.dumps(payload).encode())) as urlopen:
            response = self.client.get("/products")
        self.assertEqual(urlopen.call_count, 1)
        return response

    def test_empty_collection_returns_json_array(self):
        response = self.authenticated_get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.assertEqual(response["Content-Type"], "application/json")

    def test_all_products_are_ordered_by_id_without_pagination(self):
        for name, price in (("First", "0.00"), ("Second", "12.50"), ("Third", "99999999.99")):
            Product.objects.create(name=name, description="Description", price=Decimal(price), quantity=2)
        response = self.authenticated_get()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsInstance(body, list)
        self.assertEqual([item["name"] for item in body], ["First", "Second", "Third"])
        self.assertEqual([item["id"] for item in body], sorted(item["id"] for item in body))
        self.assertEqual([item["price"] for item in body], ["0.00", "12.50", "99999999.99"])
        self.assertEqual(set(body[0]), {"id", "name", "description", "price", "quantity", "created_at", "updated_at"})

    @patch("products.authentication.urlopen")
    def test_missing_token_returns_401_without_querying_auth(self, urlopen):
        response = self.client.get("/products")
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())
        urlopen.assert_not_called()

    @patch("products.authentication.urlopen", side_effect=URLError("offline"))
    def test_unavailable_auth_returns_503(self, urlopen):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer access-token")
        response = self.client.get("/products")
        self.assertEqual(response.status_code, 503)
        self.assertIn("detail", response.json())
        urlopen.assert_called_once()
