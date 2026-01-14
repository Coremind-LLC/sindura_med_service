from django.shortcuts import get_object_or_404

from apps.common.enums import Status
from apps.examination.models import Examination
from apps.examination.serializers import ExaminationSerializer

class ExaminationService:

    @staticmethod
    def get_all():
        queryset = Examination.objects.all()
        serializer = ExaminationSerializer(queryset, many=True)
        return serializer.data

    @staticmethod
    def get_by_id(id: int):
        instance = get_object_or_404(Examination, pk=id)
        serializer = ExaminationSerializer(instance)
        return serializer.data

    @staticmethod
    def get_locked_by_examination_pack(examination_pack_id: int):
        queryset = Examination.objects.filter(
            examination_pack_id=examination_pack_id,
            is_lock=True,
            status=Status.ACTIVE
        )
        serializer = ExaminationSerializer(queryset, many=True)
        return serializer.data

    @staticmethod
    def has_locked_by_examination_pack(examination_pack_id: int) -> bool:
        return Examination.objects.filter(
            examination_pack_id=examination_pack_id,
            is_lock=True,
            status=Status.ACTIVE
        ).exists()

    @staticmethod
    def create(data: dict, request):
        serializer = ExaminationSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def create_bulk(data: list[dict], request):
        serializer = ExaminationSerializer(
            data=data,
            many=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def update(id: int, data: dict, request):
        instance = get_object_or_404(Examination, pk=id)
        serializer = ExaminationSerializer(
            instance,
            data=data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(Examination, pk=id)
        instance.status = Status.DELETED
        instance.save(update_fields=["status"])

    @staticmethod
    def delete_by_examination_pack(examination_pack_id: int):
        return Examination.objects.filter(
            examination_pack_id=examination_pack_id,
            status=Status.ACTIVE
        ).update(status=Status.DELETED)