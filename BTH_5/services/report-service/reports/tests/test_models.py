"""Verify local database constraints and cascade deletion on reports.sqlite3."""
from datetime import datetime, timezone
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from reports.models import (
    OrderCost,
    OrderReportLine,
    ProductCost,
    ProductReportLine,
    ReportSnapshot,
)


class ModelConstraintTests(TestCase):
    def test_product_cost_constraints(self):
        ProductCost.objects.create(product_id=1, unit_cost=Decimal("5.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductCost.objects.create(product_id=1, unit_cost=Decimal("6.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductCost.objects.create(product_id=0, unit_cost=Decimal("5.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductCost.objects.create(product_id=2, unit_cost=Decimal("-1.00"))

    def test_order_cost_constraints(self):
        OrderCost.objects.create(order_id=10, additional_cost=Decimal("2.50"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderCost.objects.create(order_id=10, additional_cost=Decimal("3.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderCost.objects.create(order_id=-5, additional_cost=Decimal("1.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderCost.objects.create(order_id=11, additional_cost=Decimal("-0.01"))

    def test_snapshot_cascades_to_lines_and_allows_negative_profit(self):
        snapshot = ReportSnapshot.objects.create(
            title="Loss Quarter",
            total_revenue=Decimal("100.00"),
            total_cost=Decimal("150.00"),
            total_profit=Decimal("-50.00"),
        )
        ProductReportLine.objects.create(
            snapshot=snapshot,
            product_id=1,
            product_name="Widget",
            stock_quantity=10,
            sold_quantity=2,
            revenue=Decimal("100.00"),
            cost=Decimal("140.00"),
            profit=Decimal("-40.00"),
        )
        OrderReportLine.objects.create(
            snapshot=snapshot,
            order_id=1,
            customer_name="Alice",
            customer_email="alice@example.com",
            order_status="completed",
            order_created_at=datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc),
            item_count=1,
            total_quantity=2,
            sold_quantity=2,
            order_total_amount=Decimal("100.00"),
            revenue=Decimal("100.00"),
            product_cost=Decimal("140.00"),
            additional_cost=Decimal("10.00"),
            total_cost=Decimal("150.00"),
            profit=Decimal("-50.00"),
        )
        snapshot.delete()
        self.assertFalse(ProductReportLine.objects.exists())
        self.assertFalse(OrderReportLine.objects.exists())
