"""REST endpoints without trailing slashes, matching Product and Order Services."""
from django.urls import path

from reports.views.costs import (
    OrderCostCollectionView,
    OrderCostDetailView,
    ProductCostCollectionView,
    ProductCostDetailView,
)
from reports.views.health import HealthView
from reports.views.live_reports import (
    OrderReportDetailView,
    OrderReportView,
    ProductReportDetailView,
    ProductReportView,
    SummaryReportView,
)
from reports.views.snapshots import ReportSnapshotCollectionView, ReportSnapshotDetailView


urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("reports", ReportSnapshotCollectionView.as_view(), name="report_snapshot_collection"),
    path("reports/summary", SummaryReportView.as_view(), name="report_summary"),
    path("reports/products", ProductReportView.as_view(), name="report_products"),
    path("reports/products/<str:product_id>", ProductReportDetailView.as_view(), name="report_product_detail"),
    path("reports/orders", OrderReportView.as_view(), name="report_orders"),
    path("reports/orders/<str:order_id>", OrderReportDetailView.as_view(), name="report_order_detail"),
    path("reports/<str:report_id>", ReportSnapshotDetailView.as_view(), name="report_snapshot_detail"),
    path("product_costs", ProductCostCollectionView.as_view(), name="product_cost_collection"),
    path("product_costs/<str:product_id>", ProductCostDetailView.as_view(), name="product_cost_detail"),
    path("order_costs", OrderCostCollectionView.as_view(), name="order_cost_collection"),
    path("order_costs/<str:order_id>", OrderCostDetailView.as_view(), name="order_cost_detail"),
]
