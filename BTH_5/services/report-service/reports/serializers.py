"""Explicit request contracts and read-only response representations for Report Service."""

from collections.abc import Mapping
from decimal import Decimal

from rest_framework import serializers

from reports.models import OrderCost, OrderReportLine, ProductCost, ProductReportLine, ReportSnapshot
from reports.validation import SQLITE_MAX_INTEGER


MAX_COST_AMOUNT = Decimal("9999999999.99")


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


class StrictBooleanField(serializers.BooleanField):
    def to_internal_value(self, data):
        if type(data) is not bool:
            raise serializers.ValidationError("A JSON boolean is required.")
        return data


class StrictMoneyField(serializers.DecimalField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 12)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("min_value", Decimal("0.00"))
        kwargs.setdefault("max_value", MAX_COST_AMOUNT)
        kwargs.setdefault("coerce_to_string", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, bool):
            raise serializers.ValidationError("A valid nonnegative decimal amount is required.")
        return super().to_internal_value(data)


class ProductCostCreateSerializer(StrictFieldsMixin, serializers.Serializer):
    product_id = StrictPositiveIntegerField()
    unit_cost = StrictMoneyField()
    note = StrictTextField(max_length=255, allow_blank=True, required=False, default="")


class ProductCostUpdateSerializer(StrictFieldsMixin, serializers.Serializer):
    unit_cost = StrictMoneyField()
    note = StrictTextField(max_length=255, allow_blank=True, required=False, default="")


class ProductCostSerializer(serializers.ModelSerializer):
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, coerce_to_string=True
    )

    class Meta:
        model = ProductCost
        fields = ("id", "product_id", "unit_cost", "note", "created_at", "updated_at")
        read_only_fields = fields


class OrderCostCreateSerializer(StrictFieldsMixin, serializers.Serializer):
    order_id = StrictPositiveIntegerField()
    additional_cost = StrictMoneyField()
    note = StrictTextField(max_length=255, allow_blank=True, required=False, default="")


class OrderCostUpdateSerializer(StrictFieldsMixin, serializers.Serializer):
    additional_cost = StrictMoneyField()
    note = StrictTextField(max_length=255, allow_blank=True, required=False, default="")


class OrderCostSerializer(serializers.ModelSerializer):
    additional_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, coerce_to_string=True
    )

    class Meta:
        model = OrderCost
        fields = ("id", "order_id", "additional_cost", "note", "created_at", "updated_at")
        read_only_fields = fields


class ReportSnapshotCreateSerializer(StrictFieldsMixin, serializers.Serializer):
    title = StrictTextField(
        max_length=255, allow_blank=False, trim_whitespace=True, required=False, default="Sales & Inventory Report"
    )
    report_type = serializers.ChoiceField(
        choices=ReportSnapshot.ReportType.choices, required=False, default=ReportSnapshot.ReportType.FULL
    )
    from_date = serializers.DateField(required=False, allow_null=True, default=None, input_formats=["%Y-%m-%d"])
    to_date = serializers.DateField(required=False, allow_null=True, default=None, input_formats=["%Y-%m-%d"])
    include_pending = StrictBooleanField(required=False, default=False)

    def validate(self, attrs):
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError({"from_date": ["from_date cannot be later than to_date."]})
        return attrs


class ProductReportLineSerializer(serializers.ModelSerializer):
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, allow_null=True, coerce_to_string=True
    )
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, coerce_to_string=True
    )
    inventory_value = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    inventory_cost_value = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    revenue = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    profit = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )

    class Meta:
        model = ProductReportLine
        fields = (
            "product_id",
            "product_name",
            "in_catalog",
            "unit_price",
            "unit_cost",
            "cost_configured",
            "stock_quantity",
            "sold_quantity",
            "order_count",
            "inventory_value",
            "inventory_cost_value",
            "revenue",
            "cost",
            "profit",
        )
        read_only_fields = fields


class OrderReportLineSerializer(serializers.ModelSerializer):
    order_total_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    revenue = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    product_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    additional_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    total_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    profit = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )

    class Meta:
        model = OrderReportLine
        fields = (
            "order_id",
            "customer_name",
            "customer_email",
            "order_status",
            "order_created_at",
            "item_count",
            "total_quantity",
            "sold_quantity",
            "order_total_amount",
            "revenue",
            "product_cost",
            "additional_cost",
            "total_cost",
            "profit",
        )
        read_only_fields = fields


class ReportSnapshotListSerializer(serializers.ModelSerializer):
    total_inventory_value = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    total_inventory_cost_value = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    total_revenue = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    total_product_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    total_additional_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    total_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    total_profit = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )

    class Meta:
        model = ReportSnapshot
        fields = (
            "id",
            "title",
            "report_type",
            "from_date",
            "to_date",
            "include_pending",
            "total_products",
            "total_orders",
            "completed_orders",
            "pending_orders",
            "cancelled_orders",
            "total_stock_quantity",
            "total_sold_quantity",
            "total_inventory_value",
            "total_inventory_cost_value",
            "total_revenue",
            "total_product_cost",
            "total_additional_cost",
            "total_cost",
            "total_profit",
            "created_by",
            "created_at",
        )
        read_only_fields = fields


class ReportSnapshotDetailSerializer(ReportSnapshotListSerializer):
    product_lines = ProductReportLineSerializer(many=True, read_only=True)
    order_lines = OrderReportLineSerializer(many=True, read_only=True)

    class Meta(ReportSnapshotListSerializer.Meta):
        fields = ReportSnapshotListSerializer.Meta.fields + ("product_lines", "order_lines")
        read_only_fields = fields
