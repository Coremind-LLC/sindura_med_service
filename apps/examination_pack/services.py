from django.shortcuts import get_object_or_404

from apps.common.enums import Status
from apps.examination_pack.models import ExaminationPack
from apps.examination_pack.serializers import ExaminationPackSerializer

class ExaminationPackService:

    @staticmethod
    def get_all():
        queryset = ExaminationPack.objects.all()
        serializer = ExaminationPackSerializer(queryset, many=True)
        return serializer.data

    @staticmethod
    def get_by_id(id: int):
        instance = get_object_or_404(ExaminationPack, pk=id)
        serializer = ExaminationPackSerializer(instance)
        return serializer.data

    @staticmethod
    def create(data: dict, request):
        serializer = ExaminationPackSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def update(id: int, data: dict, request):
        instance = get_object_or_404(ExaminationPack, pk=id)
        serializer = ExaminationPackSerializer(
            instance,
            data=data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(ExaminationPack, pk=id)
        instance.status = Status.DELETED
        instance.save(update_fields=["status"])