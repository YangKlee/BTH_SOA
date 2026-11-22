from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from orders.errors import OrderAPIError
from orders.serializers import OrderDetailSerializer, OrderStatusSerializer
from orders.services import change_order_status, delete_order
from orders.validation import parse_positive_id


class OrderDetailView(APIView):
    def get(self, request, order_id):
        parsed_id = parse_positive_id(order_id)
        order = Order.objects.prefetch_related("items").filter(pk=parsed_id).first()
        if order is None:
            raise OrderAPIError(404, "order_not_found", "Order not found.")
        return Response(OrderDetailSerializer(order).data)

    def put(self, request, order_id):
        parsed_id = parse_positive_id(order_id)
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = change_order_status(parsed_id, serializer.validated_data["status"], request.auth)
        return Response(OrderDetailSerializer(order).data)

    def delete(self, request, order_id):
        delete_order(parse_positive_id(order_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
