from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.examination.services import ExaminationService
from apps.examination_pack.services import ExaminationPackService
from apps.examination_type.models import ExaminationType
from apps.examination_type.serializers import ExaminationTypeSerializer
from apps.examination_type.services import ExaminationTypeService

class ExaminationTypeViewSet(BaseViewSet):
    queryset = ExaminationType.objects.all()
    serializer_class = ExaminationTypeSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        pk = self.get_object().id
        user = request.user

        try:
            if ExaminationPackService.exists_by_examination_type(pk):
                raise ValidationError(
                    {"message": "Cannot delete examination type because they have active examination packs."}
                )

            if ExaminationService.exists_by_examination_type(pk):
                raise ValidationError(
                    {"message": "Cannot delete examination type because they have active examinations."}
                )

            ExaminationTypeService.delete(pk, user)
            return Response(
                {"message": "Examination type deleted successfully."},
                status=status.HTTP_204_NO_CONTENT
            )
        except ValidationError as e:
            return Response(
                {"message": e.detail.get("message", "Cannot delete examination type.")},
                status=status.HTTP_400_BAD_REQUEST
            )