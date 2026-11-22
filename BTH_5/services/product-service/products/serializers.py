from collections.abc import Mapping
from decimal import Decimal

from rest_framework import serializers

from products.models import Product


class StrictNonnegativeIntegerField(serializers.IntegerField):
    """Accept JSON integers only; DRF's default also coerces booleans and strings."""

    def to_internal_value(self, data):
        if type(data) is not int:
            raise serializers.ValidationError("A nonnegative integer is required.")
        return super().to_internal_value(data)


class StrictTextField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("A string is required.")
        return super().to_internal_value(data)


class ProductSerializer(serializers.ModelSerializer):
    name = StrictTextField(max_length=255, allow_blank=False, trim_whitespace=True)
    description = StrictTextField(allow_blank=False, trim_whitespace=True)
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        max_value=Decimal("99999999.99"),
        coerce_to_string=True,
    )
    quantity = StrictNonnegativeIntegerField(min_value=0)

    class Meta:
        model = Product
        fields = ("id", "name", "description", "price", "quantity", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            rejected = set(data) - {"name", "description", "price", "quantity"}
            if rejected:
                raise serializers.ValidationError(
                    {field: ["This field cannot be written."] for field in sorted(rejected)}
                )
        return super().to_internal_value(data)
