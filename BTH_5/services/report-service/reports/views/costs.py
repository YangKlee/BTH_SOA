from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.errors import ReportAPIError
from reports.models import OrderCost, ProductCost
from reports.serializers import (
    OrderCostCreateSerializer,
    OrderCostSerializer,
    OrderCostUpdateSerializer,
    ProductCostCreateSerializer,
    ProductCostSerializer,
    ProductCostUpdateSerializer,
)
from reports.services import (
    create_order_cost,
    create_product_cost,
    delete_order_cost,
    delete_product_cost,
    update_order_cost,
    update_product_cost,
)
from reports.validation import parse_positive_id


class ProductCostCollectionView(APIView):
    def get(self, request):
        return Response(ProductCostSerializer(ProductCost.objects.order_by("product_id"), many=True).data)

    def post(self, request):
        serializer = ProductCostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cost = create_product_cost(serializer.validated_data, request.auth)
        return Response(
            ProductCostSerializer(cost).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/product_costs/{cost.product_id}"},
        )


class ProductCostDetailView(APIView):
    def get(self, request, product_id):
        parsed_id = parse_positive_id(product_id, field_name="product_id")
        cost = ProductCost.objects.filter(product_id=parsed_id).first()
        if cost is None:
            raise ReportAPIError(
                404, "product_cost_not_found", "Product cost configuration not found.", product_id=parsed_id
            )
        return Response(ProductCostSerializer(cost).data)

    def put(self, request, product_id):
        parsed_id = parse_positive_id(product_id, field_name="product_id")
        serializer = ProductCostUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cost = update_product_cost(parsed_id, serializer.validated_data)
        return Response(ProductCostSerializer(cost).data)

    def delete(self, request, product_id):
        parsed_id = parse_positive_id(product_id, field_name="product_id")
        delete_product_cost(parsed_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderCostCollectionView(APIView):
    def get(self, request):
        return Response(OrderCostSerializer(OrderCost.objects.order_by("order_id"), many=True).data)

    def post(self, request):
        serializer = OrderCostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cost = create_order_cost(serializer.validated_data, request.auth)
        return Response(
            OrderCostSerializer(cost).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/order_costs/{cost.order_id}"},
        )


class OrderCostDetailView(APIView):
    def get(self, request, order_id):
        parsed_id = parse_positive_id(order_id, field_name="order_id")
        cost = OrderCost.objects.filter(order_id=parsed_id).first()
        if cost is None:
            raise ReportAPIError(
                404, "order_cost_not_found", "Order cost configuration not found.", order_id=parsed_id
            )
        return Response(OrderCostSerializer(cost).data)

    def put(self, request, order_id):
        parsed_id = parse_positive_id(order_id, field_name="order_id")
        serializer = OrderCostUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cost = update_order_cost(parsed_id, serializer.validated_data)
        return Response(OrderCostSerializer(cost).data)

    def delete(self, request, order_id):
        parsed_id = parse_positive_id(order_id, field_name="order_id")
        delete_order_cost(parsed_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
