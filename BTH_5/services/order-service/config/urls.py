"""REST endpoints without trailing slashes, matching Product Service."""
from django.urls import path

from orders.views.item_collection import ItemCollectionView
from orders.views.item_detail import ItemDetailView
from orders.views.order_collection import OrderCollectionView
from orders.views.order_detail import OrderDetailView


urlpatterns = [
    path("orders", OrderCollectionView.as_view(), name="order_collection"),
    path("orders/<str:order_id>", OrderDetailView.as_view(), name="order_detail"),
    path("order_items", ItemCollectionView.as_view(), name="item_collection"),
    path("order_items/<str:item_id>", ItemDetailView.as_view(), name="item_detail"),
]
