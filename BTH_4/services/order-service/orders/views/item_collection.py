from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import OrderItem
from orders.serializers import ItemCreateSerializer, OrderItemSerializer
from orders.services import add_item


class ItemCollectionView(APIView):
    def get(self, request):
        return Response(OrderItemSerializer(OrderItem.objects.order_by("id"), many=True).data)

    def post(self, request):
        serializer = ItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = add_item(serializer.validated_data, request.auth)
        return Response(
            OrderItemSerializer(item).data, status=status.HTTP_201_CREATED,
            headers={"Location": f"/order_items/{item.pk}"},
        )
