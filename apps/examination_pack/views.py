from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.examination.services import ExaminationService
from apps.examination_pack.models import ExaminationPack
from apps.examination_pack.serializers import ExaminationPackSerializer
from apps.examination_pack.services import ExaminationPackService

class ExaminationPackViewSet(BaseViewSet):
    queryset = ExaminationPack.objects.all()
    serializer_class = ExaminationPackSerializer

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