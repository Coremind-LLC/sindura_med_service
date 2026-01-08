from apps.common.views import BaseViewSet
from apps.examination.models import Examination
from apps.examination.serializers import ExaminationSerializer

class ExaminationViewSet(BaseViewSet):
    queryset = Examination.objects.all()
    serializer_class = ExaminationSerializer