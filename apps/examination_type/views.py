from apps.common.views import BaseViewSet
from apps.examination_type.models import ExaminationType
from apps.examination_type.serializers import ExaminationTypeSerializer

class ExaminationTypeViewSet(BaseViewSet):
    queryset = ExaminationType.objects.all()
    serializer_class = ExaminationTypeSerializer