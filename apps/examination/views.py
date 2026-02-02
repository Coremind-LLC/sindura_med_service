from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.examination.models import Examination
from apps.examination.serializers import ExaminationSerializer
from apps.examination.services import ExaminationService

class ExaminationViewSet(BaseViewSet):
    queryset = Examination.objects.all()
    serializer_class = ExaminationSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "get_available"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="available")
    def get_available(self, request):
        date_param = request.query_params.get("date")
        examination_type_param = request.query_params.get("examination_type")

        if not date_param:
            raise ValidationError({"message": "Date is required (YYYY-MM)"})

        if not examination_type_param:
            raise ValidationError({"message": "Examination type is required"})

        try:
            year, month = map(int, date_param.split("-"))
        except Exception:
            raise ValidationError({"message": "Invalid format. Use YYYY-MM"})

        examinations = ExaminationService.get_by_date_and_examination_type(year, month, examination_type_param)

        return Response(examinations)