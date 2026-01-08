from apps.common.views import BaseViewSet
from apps.doctor.models import Doctor
from apps.doctor.serializers import DoctorSerializer

class DoctorViewSet(BaseViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer