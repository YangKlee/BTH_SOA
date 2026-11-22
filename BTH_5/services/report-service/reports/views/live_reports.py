from rest_framework.response import Response
from rest_framework.views import APIView

from reports.services import (
    build_orders_report,
    build_products_report,
    build_single_order_report,
    build_single_product_report,
    build_summary_report,
)
from reports.validation import parse_bool_param, parse_positive_id, parse_report_filters


class SummaryReportView(APIView):
    def get(self, request):
        filters = parse_report_filters(request.query_params)
        payload = build_summary_report(
            request.auth,
            from_date=filters["from_date"],
            to_date=filters["to_date"],
            include_pending=filters["include_pending"],
        )
        return Response(payload)


class ProductReportView(APIView):
    def get(self, request):
        filters = parse_report_filters(request.query_params, allow_product_id=True)
        payload = build_products_report(
            request.auth,
            from_date=filters["from_date"],
            to_date=filters["to_date"],
            include_pending=filters["include_pending"],
            product_id=filters["product_id"],
        )
        return Response(payload)


class ProductReportDetailView(APIView):
    def get(self, request, product_id):
        parsed_id = parse_positive_id(product_id, field_name="product_id")
        filters = parse_report_filters(request.query_params)
        payload = build_single_product_report(
            parsed_id,
            request.auth,
            from_date=filters["from_date"],
            to_date=filters["to_date"],
            include_pending=filters["include_pending"],
        )
        return Response(payload)


class OrderReportView(APIView):
    def get(self, request):
        filters = parse_report_filters(request.query_params, allow_status=True, allow_product_id=True)
        payload = build_orders_report(
            request.auth,
            status_filter=filters["status"],
            from_date=filters["from_date"],
            to_date=filters["to_date"],
            include_pending=filters["include_pending"],
            product_id=filters["product_id"],
        )
        return Response(payload)


class OrderReportDetailView(APIView):
    def get(self, request, order_id):
        parsed_id = parse_positive_id(order_id, field_name="order_id")
        include_pending = parse_bool_param(
            request.query_params.get("include_pending"), "include_pending", default=False
        )
        payload = build_single_order_report(
            parsed_id,
            request.auth,
            include_pending=include_pending,
        )
        return Response(payload)
