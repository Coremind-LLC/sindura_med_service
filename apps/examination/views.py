from rest_framework.permissions import AllowAny, IsAuthenticated
from apps.common.views import BaseViewSet
from apps.examination.models import Examination
from apps.examination.serializers import ExaminationSerializer
from apps.third_party.qpay.services import QPayService

class ExaminationViewSet(BaseViewSet):
    queryset = Examination.objects.all()
    serializer_class = ExaminationSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            QPayService.login()

            return [AllowAny()]
        return [IsAuthenticated()]