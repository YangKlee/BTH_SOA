from decimal import Decimal

from django.db import models
from django.db.models import Q


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(max_length=255)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="orders_total_nonnegative"),
            models.CheckConstraint(
                condition=Q(status__in=["pending", "completed", "cancelled"]), name="orders_status_valid"
            ),
        ]


class OrderItem(models.Model):
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", db_column="order_id")
    product_id = models.BigIntegerField()
    product_name = models.CharField(max_length=255)
    quantity = models.BigIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_items"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(product_id__gt=0), name="order_items_product_positive"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="order_items_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="order_items_unit_nonnegative"),
            models.CheckConstraint(condition=Q(total_price__gte=0), name="order_items_total_nonnegative"),
            models.UniqueConstraint(fields=["order", "product_id"], name="order_items_order_product_unique"),
        ]
