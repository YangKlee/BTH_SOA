from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import OrderItem
from orders.errors import OrderAPIError
from orders.serializers import ItemUpdateSerializer, OrderItemSerializer
from orders.services import delete_item, update_item
from orders.validation import parse_positive_id


class ItemDetailView(APIView):
    def get(self, request, item_id):
        parsed_id = parse_positive_id(item_id)
        item = OrderItem.objects.filter(pk=parsed_id).first()
        if item is None:
            raise OrderAPIError(404, "item_not_found", "Order item not found.")
        return Response(OrderItemSerializer(item).data)

    def put(self, request, item_id):
        parsed_id = parse_positive_id(item_id)
        serializer = ItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = update_item(parsed_id, serializer.validated_data["quantity"], request.auth)
        return Response(OrderItemSerializer(item).data)

    def delete(self, request, item_id):
        delete_item(parse_positive_id(item_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
