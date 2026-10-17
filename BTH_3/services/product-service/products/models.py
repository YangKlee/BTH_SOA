from django.db import models
from django.db.models import Q


class Product(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="products_price_nonnegative"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="products_quantity_nonnegative"),
        ]
