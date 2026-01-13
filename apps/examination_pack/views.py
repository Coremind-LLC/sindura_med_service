from apps.common.views import BaseViewSet
from apps.examination_pack.models import ExaminationPack
from apps.examination_pack.serializers import ExaminationPackSerializer

class ExaminationPackViewSet(BaseViewSet):
    queryset = ExaminationPack.objects.all()
    serializer_class = ExaminationPackSerializer