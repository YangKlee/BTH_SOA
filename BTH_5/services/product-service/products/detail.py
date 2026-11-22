"""Detail endpoint for a single product."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import ProductSerializer


def parse_product_id(product_id):
    """Return a positive SQLite integer ID, or None for invalid path input."""
    if (
        not product_id.isascii()
        or not product_id.isdigit()
        or len(product_id) > 19
    ):
        return None
    value = int(product_id)
    return value if 0 < value <= 9223372036854775807 else None


class ProductDetailView(APIView):
    def get(self, request, product_id):
        parsed_id = parse_product_id(product_id)
        if parsed_id is None:
            return Response(
                {"detail": "Product id must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = Product.objects.filter(pk=parsed_id).first()
        if product is None:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProductSerializer(product).data)

    def put(self, request, product_id):
        parsed_id = parse_product_id(product_id)
        if parsed_id is None:
            return Response(
                {"detail": "Product id must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = Product.objects.filter(pk=parsed_id).first()
        if product is None:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProductSerializer(product, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, product_id):
        parsed_id = parse_product_id(product_id)
        if parsed_id is None:
            return Response(
                {"detail": "Product id must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = Product.objects.filter(pk=parsed_id).delete()
        if deleted_count == 0:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
