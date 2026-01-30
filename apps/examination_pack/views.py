from calendar import monthrange
from datetime import date

from django.db import transaction
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.examination.services import ExaminationService
from apps.examination_pack.models import ExaminationPack
from apps.examination_pack.serializers import ExaminationPackSerializer
from apps.examination_pack.services import ExaminationPackService

class ExaminationPackViewSet(BaseViewSet):
    queryset = ExaminationPack.objects.all()
    serializer_class = ExaminationPackSerializer

    def get_permissions(self):
        if self.action == "get_available":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        dates = request.query_params.getlist("dates")

        try:
            queryset = ExaminationPackService.search_by_dates(dates)
        except ValueError:
            return Response(
                {"message": "Dates must be in YYYY-MM-DD format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="available")
    def get_available(self, request):
        date_param = request.query_params.get("date")

        if not date_param:
            raise ValidationError({"message": "Date is required (YYYY-MM)"})

        try:
            year, month = map(int, date_param.split("-"))
        except Exception:
            raise ValidationError({"message": "Invalid format. Use YYYY-MM"})

        packs = ExaminationPackService.get_by_month(year, month)

        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        today = date.today()

        available_list = sorted({
            d
            for pack in packs
            for d in pack.dates
            if start_date <= d <= end_date and d >= today
        })

        return Response({
            "month": f"{year}-{month:02d}",
            "days": [d.day for d in available_list],
        })

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if ExaminationService.has_locked_by_examination_pack(instance.id):
            return Response(
                {"detail": "Cannot delete this examination pack because it has locked examinations."},
                status=status.HTTP_400_BAD_REQUEST
            )

        ExaminationService.delete_by_examination_pack(instance.id)
        ExaminationPackService.delete(instance.id)

        return Response(status=status.HTTP_204_NO_CONTENT)