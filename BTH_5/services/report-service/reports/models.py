from decimal import Decimal

from django.db import models
from django.db.models import Q


class ProductCost(models.Model):
    """Per-product unit cost (COGS) owned exclusively by Report Service."""

    id = models.AutoField(primary_key=True)
    product_id = models.BigIntegerField(unique=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_costs"
        ordering = ["product_id"]
        constraints = [
            models.CheckConstraint(condition=Q(product_id__gt=0), name="product_costs_product_positive"),
            models.CheckConstraint(condition=Q(unit_cost__gte=0), name="product_costs_unit_nonnegative"),
        ]


class OrderCost(models.Model):
    """Additional order-level expenses (shipping, packaging, fees) owned by Report Service."""

    id = models.AutoField(primary_key=True)
    order_id = models.BigIntegerField(unique=True)
    additional_cost = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_costs"
        ordering = ["order_id"]
        constraints = [
            models.CheckConstraint(condition=Q(order_id__gt=0), name="order_costs_order_positive"),
            models.CheckConstraint(condition=Q(additional_cost__gte=0), name="order_costs_amount_nonnegative"),
        ]


class ReportSnapshot(models.Model):
    """Persisted point-in-time statistical report stored in reports.sqlite3."""

    class ReportType(models.TextChoices):
        FULL = "full", "Full"
        PRODUCTS = "products", "Products"
        ORDERS = "orders", "Orders"

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=32, choices=ReportType.choices, default=ReportType.FULL)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    include_pending = models.BooleanField(default=False)

    total_products = models.BigIntegerField(default=0)
    total_orders = models.BigIntegerField(default=0)
    completed_orders = models.BigIntegerField(default=0)
    pending_orders = models.BigIntegerField(default=0)
    cancelled_orders = models.BigIntegerField(default=0)

    total_stock_quantity = models.BigIntegerField(default=0)
    total_sold_quantity = models.BigIntegerField(default=0)

    total_inventory_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_inventory_cost_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_product_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_additional_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    created_by = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "report_snapshots"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(report_type__in=["full", "products", "orders"]),
                name="report_snapshots_type_valid",
            ),
            models.CheckConstraint(condition=Q(total_products__gte=0), name="report_snapshots_products_nonneg"),
            models.CheckConstraint(condition=Q(total_orders__gte=0), name="report_snapshots_orders_nonneg"),
            models.CheckConstraint(condition=Q(total_stock_quantity__gte=0), name="report_snapshots_stock_nonneg"),
            models.CheckConstraint(condition=Q(total_sold_quantity__gte=0), name="report_snapshots_sold_nonneg"),
            models.CheckConstraint(condition=Q(total_revenue__gte=0), name="report_snapshots_revenue_nonneg"),
            models.CheckConstraint(condition=Q(total_cost__gte=0), name="report_snapshots_cost_nonneg"),
        ]


class ProductReportLine(models.Model):
    """Per-product statistics captured inside a ReportSnapshot."""

    id = models.AutoField(primary_key=True)
    snapshot = models.ForeignKey(
        ReportSnapshot, on_delete=models.CASCADE, related_name="product_lines", db_column="snapshot_id"
    )
    product_id = models.BigIntegerField()
    product_name = models.CharField(max_length=255)
    in_catalog = models.BooleanField(default=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cost_configured = models.BooleanField(default=False)
    stock_quantity = models.BigIntegerField(default=0)
    sold_quantity = models.BigIntegerField(default=0)
    order_count = models.BigIntegerField(default=0)
    inventory_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    inventory_cost_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "product_report_lines"
        ordering = ["product_id"]
        constraints = [
            models.CheckConstraint(condition=Q(product_id__gt=0), name="product_report_lines_product_positive"),
            models.CheckConstraint(condition=Q(stock_quantity__gte=0), name="product_report_lines_stock_nonneg"),
            models.CheckConstraint(condition=Q(sold_quantity__gte=0), name="product_report_lines_sold_nonneg"),
            models.UniqueConstraint(
                fields=["snapshot", "product_id"], name="product_report_lines_snapshot_product_unique"
            ),
        ]


class OrderReportLine(models.Model):
    """Per-order statistics captured inside a ReportSnapshot."""

    id = models.AutoField(primary_key=True)
    snapshot = models.ForeignKey(
        ReportSnapshot, on_delete=models.CASCADE, related_name="order_lines", db_column="snapshot_id"
    )
    order_id = models.BigIntegerField()
    customer_name = models.CharField(max_length=255)
    customer_email = models.CharField(max_length=255)
    order_status = models.CharField(max_length=50)
    order_created_at = models.DateTimeField()
    item_count = models.BigIntegerField(default=0)
    total_quantity = models.BigIntegerField(default=0)
    sold_quantity = models.BigIntegerField(default=0)
    order_total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    product_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    additional_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "order_report_lines"
        ordering = ["order_id"]
        constraints = [
            models.CheckConstraint(condition=Q(order_id__gt=0), name="order_report_lines_order_positive"),
            models.CheckConstraint(condition=Q(item_count__gte=0), name="order_report_lines_items_nonneg"),
            models.CheckConstraint(condition=Q(total_quantity__gte=0), name="order_report_lines_qty_nonneg"),
            models.CheckConstraint(condition=Q(sold_quantity__gte=0), name="order_report_lines_sold_nonneg"),
            models.UniqueConstraint(
                fields=["snapshot", "order_id"], name="order_report_lines_snapshot_order_unique"
            ),
        ]
