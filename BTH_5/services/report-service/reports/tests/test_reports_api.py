"""Comprehensive API tests for summary, product, order reports, and persisted snapshots."""
import io
import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from rest_framework.test import APITestCase

from reports.clients.order import OrderItemSnapshot, OrderSnapshot
from reports.clients.product import ProductSnapshot
from reports.errors import ReportAPIError
from reports.models import OrderCost, ProductCost, ReportSnapshot


def auth_response(*args, **kwargs):
    response = io.BytesIO(json.dumps({"user_id": "user-1", "email": "analyst@example.com", "role": 1}).encode())
    response.status = 200
    return response


class ReportsAPITests(APITestCase):
    def setUp(self):
        self.auth_patch = patch("reports.authentication.open_service", side_effect=auth_response)
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer good-token")

        # Catalog products:
        # P1: Pen, price 10.00, stock 50, unit_cost 6.00
        # P2: Book, price 20.00, stock 0 (out of stock), unit_cost 12.00
        # P3: Eraser, price 2.00, stock 30, NO unit_cost configured (defaults 0.00)
        self.products = [
            ProductSnapshot(1, "Pen", Decimal("10.00"), 50),
            ProductSnapshot(2, "Book", Decimal("20.00"), 0),
            ProductSnapshot(3, "Eraser", Decimal("2.00"), 30),
        ]

        # Orders:
        # O1 (completed, 2026-11-10): 3x P1 (@10.00=30.00) + 2x P2 (@20.00=40.00) => total 70.00, add_cost 5.00
        # O2 (pending,   2026-11-15): 4x P1 (@10.00=40.00) => total 40.00, add_cost 2.00
        # O3 (cancelled, 2026-11-16): 5x P3 (@2.00=10.00)  => total 10.00
        # O4 (completed, 2026-11-20): 1x P99 (deleted product, @15.00=15.00) => total 15.00, unit_cost 20.00 (loss!)
        self.orders = [
            OrderSnapshot(
                1, "Alice", "alice@example.com", Decimal("70.00"), "completed",
                datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc),
            ),
            OrderSnapshot(
                2, "Bob", "bob@example.com", Decimal("40.00"), "pending",
                datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc),
            ),
            OrderSnapshot(
                3, "Carol", "carol@example.com", Decimal("10.00"), "cancelled",
                datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 16, 13, 0, tzinfo=timezone.utc),
            ),
            OrderSnapshot(
                4, "Dave", "dave@example.com", Decimal("15.00"), "completed",
                datetime(2026, 11, 20, 14, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc),
            ),
        ]
        self.order_items = [
            OrderItemSnapshot(1, 1, 1, "Pen", 3, Decimal("10.00"), Decimal("30.00")),
            OrderItemSnapshot(2, 1, 2, "Book", 2, Decimal("20.00"), Decimal("40.00")),
            OrderItemSnapshot(3, 2, 1, "Pen", 4, Decimal("10.00"), Decimal("40.00")),
            OrderItemSnapshot(4, 3, 3, "Eraser", 5, Decimal("2.00"), Decimal("10.00")),
            OrderItemSnapshot(5, 4, 99, "Archived Lamp", 1, Decimal("15.00"), Decimal("15.00")),
        ]

        ProductCost.objects.create(product_id=1, unit_cost=Decimal("6.00"))
        ProductCost.objects.create(product_id=2, unit_cost=Decimal("12.00"))
        ProductCost.objects.create(product_id=99, unit_cost=Decimal("20.00"))
        OrderCost.objects.create(order_id=1, additional_cost=Decimal("5.00"), note="Shipping")
        OrderCost.objects.create(order_id=2, additional_cost=Decimal("2.00"), note="Pending shipping")

        self.p_patch = patch("reports.services.list_products", side_effect=lambda tok: list(self.products))
        self.o_patch = patch("reports.services.list_orders", side_effect=lambda tok: list(self.orders))
        self.i_patch = patch("reports.services.list_order_items", side_effect=lambda tok: list(self.order_items))
        self.p_patch.start()
        self.o_patch.start()
        self.i_patch.start()
        self.addCleanup(self.p_patch.stop)
        self.addCleanup(self.o_patch.stop)
        self.addCleanup(self.i_patch.stop)

    def test_summary_report_default_counts_completed_orders_only(self):
        res = self.client.get("/reports/summary")
        self.assertEqual(res.status_code, 200, res.data)
        inv = res.data["inventory"]
        sales = res.data["sales"]
        fin = res.data["financials"]

        # Stock: P1=50 (val 500, cost 300), P2=0, P3=30 (val 60, cost 0), P99(deleted)=0
        self.assertEqual(inv["total_products"], 4)
        self.assertEqual(inv["in_stock_products"], 2)
        self.assertEqual(inv["out_of_stock_products"], 1)
        self.assertEqual(inv["total_stock_quantity"], 80)
        self.assertEqual(inv["total_inventory_value"], "560.00")
        self.assertEqual(inv["total_inventory_cost_value"], "300.00")

        # Sales (completed: O1 + O4): sold = 3 + 2 + 1 = 6
        self.assertEqual(sales["total_orders"], 4)
        self.assertEqual(sales["completed_orders"], 2)
        self.assertEqual(sales["pending_orders"], 1)
        self.assertEqual(sales["cancelled_orders"], 1)
        self.assertEqual(sales["counted_orders"], 2)
        self.assertEqual(sales["total_sold_quantity"], 6)

        # Financials:
        # Revenue = 70.00 + 15.00 = 85.00
        # Product cost = (3*6 + 2*12) + (1*20) = 42.00 + 20.00 = 62.00
        # Additional cost = 5.00 (O1 only; O2 is pending)
        # Total cost = 67.00
        # Profit = 85.00 - 67.00 = 18.00
        self.assertEqual(fin["total_revenue"], "85.00")
        self.assertEqual(fin["total_product_cost"], "62.00")
        self.assertEqual(fin["total_additional_cost"], "5.00")
        self.assertEqual(fin["total_cost"], "67.00")
        self.assertEqual(fin["total_profit"], "18.00")
        self.assertEqual(fin["profit_margin_percent"], "21.18")

    def test_summary_report_with_include_pending_and_date_filter(self):
        res = self.client.get("/reports/summary?from_date=2026-11-10&to_date=2026-11-15&include_pending=true")
        self.assertEqual(res.status_code, 200, res.data)
        # Matches O1 (completed) + O2 (pending)
        # Sold = 3 + 2 + 4 = 9; Rev = 70 + 40 = 110.00
        # Product cost = 42 + 4*6 = 66.00; Additional = 5 + 2 = 7.00; Total cost = 73.00; Profit = 37.00
        self.assertEqual(res.data["sales"]["total_orders"], 2)
        self.assertEqual(res.data["sales"]["counted_orders"], 2)
        self.assertEqual(res.data["sales"]["total_sold_quantity"], 9)
        self.assertEqual(res.data["financials"]["total_revenue"], "110.00")
        self.assertEqual(res.data["financials"]["total_cost"], "73.00")
        self.assertEqual(res.data["financials"]["total_profit"], "37.00")

    def test_products_report_and_reconciliation_including_deleted_product(self):
        res = self.client.get("/reports/products")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["totals"]["total_stock_quantity"], 80)
        self.assertEqual(res.data["totals"]["total_sold_quantity"], 6)
        self.assertEqual(res.data["totals"]["total_revenue"], "85.00")
        self.assertEqual(res.data["totals"]["total_cost"], "62.00")
        self.assertEqual(res.data["totals"]["total_profit"], "23.00")

        by_id = {p["product_id"]: p for p in res.data["products"]}
        # P1
        self.assertEqual(by_id[1]["stock_quantity"], 50)
        self.assertEqual(by_id[1]["sold_quantity"], 3)
        self.assertEqual(by_id[1]["revenue"], "30.00")
        self.assertEqual(by_id[1]["cost"], "18.00")
        self.assertEqual(by_id[1]["profit"], "12.00")
        self.assertEqual(by_id[1]["profit_margin_percent"], "40.00")
        # P3 (unconfigured cost, only cancelled order -> 0 sold)
        self.assertFalse(by_id[3]["cost_configured"])
        self.assertEqual(by_id[3]["sold_quantity"], 0)
        self.assertIsNone(by_id[3]["profit_margin_percent"])
        # P99 (deleted from catalog, negative profit!)
        self.assertFalse(by_id[99]["in_catalog"])
        self.assertIsNone(by_id[99]["unit_price"])
        self.assertEqual(by_id[99]["stock_quantity"], 0)
        self.assertEqual(by_id[99]["sold_quantity"], 1)
        self.assertEqual(by_id[99]["revenue"], "15.00")
        self.assertEqual(by_id[99]["cost"], "20.00")
        self.assertEqual(by_id[99]["profit"], "-5.00")
        self.assertEqual(by_id[99]["profit_margin_percent"], "-33.33")

    def test_single_product_report(self):
        with patch("reports.services.get_product", return_value=self.products[0]):
            res = self.client.get("/reports/products/1")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["product"]["product_name"], "Pen")
        self.assertEqual(res.data["product"]["sold_quantity"], 3)
        self.assertEqual(res.data["product"]["profit"], "12.00")

        with patch("reports.services.get_product", return_value=None):
            missing = self.client.get("/reports/products/777")
        self.assertEqual(missing.status_code, 404)

    def test_orders_report_filters_and_single_order_report(self):
        res = self.client.get("/reports/orders")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["totals"]["order_count"], 4)
        self.assertEqual(res.data["totals"]["total_revenue"], "85.00")
        self.assertEqual(res.data["totals"]["total_cost"], "67.00")
        self.assertEqual(res.data["totals"]["total_profit"], "18.00")

        by_id = {o["order_id"]: o for o in res.data["orders"]}
        self.assertEqual(by_id[1]["revenue"], "70.00")
        self.assertEqual(by_id[1]["product_cost"], "42.00")
        self.assertEqual(by_id[1]["additional_cost"], "5.00")
        self.assertEqual(by_id[1]["total_cost"], "47.00")
        self.assertEqual(by_id[1]["profit"], "23.00")
        self.assertEqual(len(by_id[1]["items"]), 2)
        # Pending order excluded from realized metrics by default
        self.assertEqual(by_id[2]["revenue"], "0.00")
        self.assertEqual(by_id[2]["order_total_amount"], "40.00")
        # Cancelled order never counted
        self.assertEqual(by_id[3]["revenue"], "0.00")
        # Negative profit order
        self.assertEqual(by_id[4]["profit"], "-5.00")

        # Filter by status and product_id
        filtered = self.client.get("/reports/orders?status=completed&product_id=1")
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual([o["order_id"] for o in filtered.data["orders"]], [1])

        # Single order report
        order_one_detail = OrderSnapshot(
            1,
            "Alice",
            "alice@example.com",
            Decimal("70.00"),
            "completed",
            self.orders[0].created_at,
            self.orders[0].updated_at,
            items=(self.order_items[0], self.order_items[1]),
        )
        with patch("reports.services.get_order", return_value=order_one_detail):
            single = self.client.get("/reports/orders/1")
        self.assertEqual(single.status_code, 200)
        self.assertEqual(single.data["order"]["profit"], "23.00")

    def test_invalid_query_parameters_return_400(self):
        for url in (
            "/reports/summary?from_date=2026-11-20&to_date=2026-11-10",
            "/reports/summary?from_date=not-a-date",
            "/reports/summary?include_pending=maybe",
            "/reports/orders?status=shipped",
            "/reports/products?product_id=0",
            "/reports/products/abc",
            "/reports/orders/0",
            "/reports/0",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 400)

    def test_snapshot_create_read_without_upstream_and_delete(self):
        created = self.client.post(
            "/reports",
            {"title": "November Full Report", "report_type": "full"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        snapshot_id = created.data["id"]
        self.assertEqual(created["Location"], f"/reports/{snapshot_id}")
        self.assertEqual(created.data["total_stock_quantity"], 80)
        self.assertEqual(created.data["total_sold_quantity"], 6)
        self.assertEqual(created.data["total_revenue"], "85.00")
        self.assertEqual(created.data["total_cost"], "67.00")
        self.assertEqual(created.data["total_profit"], "18.00")
        self.assertEqual(created.data["created_by"], "analyst@example.com")
        self.assertEqual(len(created.data["product_lines"]), 4)
        self.assertEqual(len(created.data["order_lines"]), 4)

        # Reading saved snapshots must NOT call upstream Product or Order services!
        with (
            patch("reports.services.list_products", side_effect=AssertionError("Must not call Product")),
            patch("reports.services.list_orders", side_effect=AssertionError("Must not call Order")),
            patch("reports.services.list_order_items", side_effect=AssertionError("Must not call Order")),
        ):
            listing = self.client.get("/reports")
            self.assertEqual(listing.status_code, 200)
            self.assertEqual(len(listing.data), 1)
            self.assertNotIn("product_lines", listing.data[0])

            detail = self.client.get(f"/reports/{snapshot_id}")
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.data["total_profit"], "18.00")
            self.assertEqual(len(detail.data["product_lines"]), 4)
            self.assertEqual(len(detail.data["order_lines"]), 4)

        self.assertEqual(self.client.delete(f"/reports/{snapshot_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/reports/{snapshot_id}").status_code, 404)
        self.assertFalse(ReportSnapshot.objects.exists())

    def test_upstream_failure_propagates_503_and_does_not_persist_snapshot(self):
        with patch(
            "reports.services.list_products",
            side_effect=ReportAPIError(503, "product_unavailable", "Down"),
        ):
            res = self.client.post("/reports", {"title": "Should Fail"}, format="json")
        self.assertEqual(res.status_code, 503)
        self.assertFalse(ReportSnapshot.objects.exists())
