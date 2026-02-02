from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from apps.common.views import BaseViewSet
from apps.doctor.models import Doctor
from apps.doctor.serializers import DoctorSerializer
from apps.doctor.services import DoctorService
from apps.examination.services import ExaminationService
from apps.examination_pack.services import ExaminationPackService

class DoctorViewSet(BaseViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        pk = self.get_object().id
        user = request.user

        try:
            if ExaminationPackService.exists_by_doctor(pk):
                raise ValidationError(
                    {"message": "Cannot delete doctor because they have active examination packs."}
                )

            if ExaminationService.exists_by_doctor(pk):
                raise ValidationError(
                    {"message": "Cannot delete doctor because they have active examinations."}
                )

            DoctorService.delete(pk, user)
            return Response(
                {"message": "Doctor deleted successfully."},
                status=status.HTTP_204_NO_CONTENT
            )
        except ValidationError as e:
            return Response(
                {"message": e.detail.get("message", "Cannot delete doctor.")},
                status=status.HTTP_400_BAD_REQUEST
            )