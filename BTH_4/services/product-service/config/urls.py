"""Product Service API routes."""

from django.urls import path

from products.collection import ProductCollectionView
from products.detail import ProductDetailView


urlpatterns = [
    path("products", ProductCollectionView.as_view(), name="product_collection"),
    path("products/<str:product_id>", ProductDetailView.as_view(), name="product_detail"),
]
