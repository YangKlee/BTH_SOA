from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from orders.serializers import OrderCreateSerializer, OrderDetailSerializer, OrderListSerializer
from orders.services import create_order


class OrderCollectionView(APIView):
    def get(self, request):
        return Response(OrderListSerializer(Order.objects.order_by("id"), many=True).data)

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_order(serializer.validated_data, request.auth)
        return Response(
            OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED,
            headers={"Location": f"/orders/{order.pk}"},
        )
