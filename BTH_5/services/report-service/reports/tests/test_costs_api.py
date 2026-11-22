"""Test product_costs and order_costs CRUD endpoints and cross-service validation."""
import io
import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from rest_framework.test import APITestCase

from reports.clients.order import OrderSnapshot
from reports.clients.product import ProductSnapshot
from reports.errors import ReportAPIError


def auth_response(*args, **kwargs):
    response = io.BytesIO(json.dumps({"user_id": "user-1", "email": "admin@example.com", "role": 1}).encode())
    response.status = 200
    return response


class CostAPITests(APITestCase):
    def setUp(self):
        self.auth_patch = patch("reports.authentication.open_service", side_effect=auth_response)
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer good-token")

    def test_product_cost_crud_and_validation(self):
        with patch(
            "reports.services.get_product",
            return_value=ProductSnapshot(1, "Pen", Decimal("10.00"), 100),
        ) as mock_get:
            res = self.client.post(
                "/product_costs", {"product_id": 1, "unit_cost": "6.25", "note": "Supplier A"}, format="json"
            )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res["Location"], "/product_costs/1")
        self.assertEqual(res.data["unit_cost"], "6.25")
        mock_get.assert_called_once_with(1, "good-token", missing_status=400)

        # Duplicate rejected with 409
        res = self.client.post("/product_costs", {"product_id": 1, "unit_cost": "7.00"}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["code"], "product_cost_exists")

        # List & detail
        self.assertEqual(len(self.client.get("/product_costs").data), 1)
        detail = self.client.get("/product_costs/1")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["note"], "Supplier A")

        # Update
        updated = self.client.put("/product_costs/1", {"unit_cost": "7.50", "note": "Updated"}, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["unit_cost"], "7.50")

        # Unknown field rejected
        bad = self.client.put("/product_costs/1", {"unit_cost": "7.50", "extra": 1}, format="json")
        self.assertEqual(bad.status_code, 400)

        # Delete & 404 after delete
        self.assertEqual(self.client.delete("/product_costs/1").status_code, 204)
        self.assertEqual(self.client.get("/product_costs/1").status_code, 404)
        self.assertEqual(self.client.delete("/product_costs/1").status_code, 404)

    def test_product_cost_missing_upstream_product_returns_400(self):
        with patch(
            "reports.services.get_product",
            side_effect=ReportAPIError(400, "product_not_found", "Product does not exist.", product_id=99),
        ):
            res = self.client.post("/product_costs", {"product_id": 99, "unit_cost": "5.00"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "product_not_found")

    def test_order_cost_crud_and_validation(self):
        now = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
        with patch(
            "reports.services.get_order",
            return_value=OrderSnapshot(5, "Alice", "alice@example.com", Decimal("50.00"), "completed", now, now),
        ) as mock_get:
            res = self.client.post(
                "/order_costs", {"order_id": 5, "additional_cost": "3.50", "note": "Shipping"}, format="json"
            )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res["Location"], "/order_costs/5")
        self.assertEqual(res.data["additional_cost"], "3.50")
        mock_get.assert_called_once_with(5, "good-token", missing_status=400)

        self.assertEqual(
            self.client.post("/order_costs", {"order_id": 5, "additional_cost": "1.00"}, format="json").status_code,
            409,
        )
        self.assertEqual(len(self.client.get("/order_costs").data), 1)
        self.assertEqual(
            self.client.put("/order_costs/5", {"additional_cost": "4.00", "note": "Express"}, format="json").data[
                "additional_cost"
            ],
            "4.00",
        )
        self.assertEqual(self.client.delete("/order_costs/5").status_code, 204)
        self.assertEqual(self.client.get("/order_costs/5").status_code, 404)
