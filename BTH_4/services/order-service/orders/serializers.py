"""Explicit request contracts and read-only response representations."""
from collections.abc import Mapping

from rest_framework import serializers

from .models import Order, OrderItem
from .validation import SQLITE_MAX_INTEGER


class StrictFieldsMixin:
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            rejected = set(data) - set(self.fields)
            if rejected:
                raise serializers.ValidationError(
                    {field: ["This field cannot be written."] for field in sorted(rejected)}
                )
        return super().to_internal_value(data)


class StrictPositiveIntegerField(serializers.IntegerField):
    def __init__(self, **kwargs):
        kwargs.setdefault("min_value", 1)
        kwargs.setdefault("max_value", SQLITE_MAX_INTEGER)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if type(data) is not int:
            raise serializers.ValidationError("A positive JSON integer is required.")
        return super().to_internal_value(data)


class StrictTextField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("A string is required.")
        return super().to_internal_value(data)


class StrictEmailField(serializers.EmailField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("A string is required.")
        return super().to_internal_value(data)


class OrderCreateItemSerializer(StrictFieldsMixin, serializers.Serializer):
    product_id = StrictPositiveIntegerField()
    quantity = StrictPositiveIntegerField()


class OrderCreateSerializer(StrictFieldsMixin, serializers.Serializer):
    customer_name = StrictTextField(max_length=255, allow_blank=False, trim_whitespace=True)
    customer_email = StrictEmailField(max_length=255, allow_blank=False, trim_whitespace=True)
    items = OrderCreateItemSerializer(many=True, allow_empty=False)

    def validate_items(self, value):
        ids = [item["product_id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("A product may appear only once in an order.")
        return value


class OrderStatusSerializer(StrictFieldsMixin, serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


class ItemCreateSerializer(StrictFieldsMixin, serializers.Serializer):
    order_id = StrictPositiveIntegerField()
    product_id = StrictPositiveIntegerField()
    quantity = StrictPositiveIntegerField()


class ItemUpdateSerializer(StrictFieldsMixin, serializers.Serializer):
    quantity = StrictPositiveIntegerField()


class OrderItemSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, coerce_to_string=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, coerce_to_string=True)

    class Meta:
        model = OrderItem
        fields = ("id", "order_id", "product_id", "product_name", "quantity", "unit_price", "total_price")
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, coerce_to_string=True)

    class Meta:
        model = Order
        fields = ("id", "customer_name", "customer_email", "total_amount", "status", "created_at", "updated_at")
        read_only_fields = fields


class OrderDetailSerializer(OrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + ("items",)
        read_only_fields = fields
