from django.db.models import QuerySet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.common.enums import Status
from apps.common.views import BaseViewSet
from apps.examination.services import ExaminationService
from apps.examination_pack.services import ExaminationPackService
from apps.examination_type.models import ExaminationType
from apps.examination_type.serializers import ExaminationTypeSerializer
from apps.examination_type.services import ExaminationTypeService

class ExaminationTypeViewSet(BaseViewSet):
    queryset = ExaminationType.objects.all()
    serializer_class = ExaminationTypeSerializer

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet[ExaminationType]:
        archived_param = self.request.query_params.get("archived")
        if archived_param is None:
            return super().get_queryset()

        # ``?archived=`` replaces the default archived=False list filter but must keep the
        # soft-delete (status) filter that BaseViewSet applies to lists.
        queryset = self.queryset.filter(archived=archived_param.lower() == "true")
        if self.action == "list":
            queryset = queryset.filter(status=Status.ACTIVE)
        return queryset

    def destroy(self, request, *args, **kwargs) -> Response:
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

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def archive(self, request, pk=None) -> Response:
        """Archive an examination type"""
        examination_type = self.get_object()
        examination_type.archived = True
        examination_type.save()
        serializer = self.get_serializer(examination_type)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def unarchive(self, request, pk=None) -> Response:
        """Unarchive an examination type"""
        examination_type = self.get_object()
        examination_type.archived = False
        examination_type.save()
        serializer = self.get_serializer(examination_type)
        return Response(serializer.data, status=status.HTTP_200_OK)
