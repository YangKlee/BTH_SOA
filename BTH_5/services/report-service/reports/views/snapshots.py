from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.errors import ReportAPIError
from reports.models import ReportSnapshot
from reports.serializers import (
    ReportSnapshotCreateSerializer,
    ReportSnapshotDetailSerializer,
    ReportSnapshotListSerializer,
)
from reports.services import create_report_snapshot, delete_report_snapshot
from reports.validation import parse_positive_id


class ReportSnapshotCollectionView(APIView):
    def get(self, request):
        snapshots = ReportSnapshot.objects.order_by("id")
        return Response(ReportSnapshotListSerializer(snapshots, many=True).data)

    def post(self, request):
        serializer = ReportSnapshotCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        snapshot = create_report_snapshot(serializer.validated_data, request.user, request.auth)
        return Response(
            ReportSnapshotDetailSerializer(snapshot).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/reports/{snapshot.pk}"},
        )


class ReportSnapshotDetailView(APIView):
    def get(self, request, report_id):
        parsed_id = parse_positive_id(report_id)
        snapshot = (
            ReportSnapshot.objects.prefetch_related("product_lines", "order_lines")
            .filter(pk=parsed_id)
            .first()
        )
        if snapshot is None:
            raise ReportAPIError(404, "report_not_found", "Report snapshot not found.")
        return Response(ReportSnapshotDetailSerializer(snapshot).data)

    def delete(self, request, report_id):
        delete_report_snapshot(parse_positive_id(report_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
