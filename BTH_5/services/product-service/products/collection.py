"""Collection endpoint for products."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import ProductSerializer


class ProductCollectionView(APIView):
    def get(self, request):
        products = Product.objects.order_by("id")
        return Response(ProductSerializer(products, many=True).data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            ProductSerializer(product).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/products/{product.pk}"},
        )
