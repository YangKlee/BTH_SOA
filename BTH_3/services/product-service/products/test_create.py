import io
import json
from unittest.mock import patch
from urllib.error import URLError

from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Product


class FakeHTTPResponse(io.BytesIO):
    status = 200


class ProductCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def payload(self, **changes):
        data = {
            "name": "  Bút bi  ",
            "description": "  Mực xanh  ",
            "price": "12000.00",
            "quantity": 30,
        }
        data.update(changes)
        return data

    def authenticated_post(self, data):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer access-token")
        identity = {"user_id": "u-1", "email": "u@example.com", "role": 0}
        with patch("products.authentication.urlopen", return_value=FakeHTTPResponse(json.dumps(identity).encode())) as urlopen:
            response = self.client.post("/products", data, format="json")
        urlopen.assert_called_once()
        return response

    def test_creates_product_and_returns_location_and_representation(self):
        response = self.authenticated_post(self.payload())
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(response["Location"], f"/products/{body['id']}")
        self.assertEqual(body["name"], "Bút bi")
        self.assertEqual(body["description"], "Mực xanh")
        self.assertEqual(body["price"], "12000.00")
        self.assertEqual(body["quantity"], 30)
        self.assertIn("created_at", body)
        self.assertIn("updated_at", body)
        saved = Product.objects.get(pk=body["id"])
        self.assertEqual(saved.name, "Bút bi")
        self.assertEqual(saved.quantity, 30)

    def test_duplicate_name_is_allowed(self):
        self.assertEqual(self.authenticated_post(self.payload()).status_code, 201)
        self.assertEqual(self.authenticated_post(self.payload()).status_code, 201)
        self.assertEqual(Product.objects.filter(name="Bút bi").count(), 2)

    def test_missing_or_invalid_fields_return_400_without_creating(self):
        missing_name = self.payload()
        del missing_name["name"]
        cases = (
            (missing_name, "name"),
            (self.payload(price="-1.00"), "price"),
            (self.payload(quantity=1.5), "quantity"),
            (self.payload(other="unexpected"), "other"),
            (self.payload(id=123), "id"),
        )
        for data, field in cases:
            with self.subTest(field=field):
                response = self.authenticated_post(data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertEqual(Product.objects.count(), 0)

    @patch("products.authentication.urlopen")
    def test_missing_token_returns_401_without_creation(self, urlopen):
        response = self.client.post("/products", self.payload(), format="json")
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())
        self.assertEqual(Product.objects.count(), 0)
        urlopen.assert_not_called()

    @patch("products.authentication.urlopen", side_effect=URLError("offline"))
    def test_unavailable_auth_returns_503_without_creation(self, urlopen):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer access-token")
        response = self.client.post("/products", self.payload(), format="json")
        self.assertEqual(response.status_code, 503)
        self.assertIn("detail", response.json())
        self.assertEqual(Product.objects.count(), 0)
        urlopen.assert_called_once()
