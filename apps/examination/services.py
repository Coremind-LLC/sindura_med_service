from django.shortcuts import get_object_or_404

from apps.common.enums import Status
from apps.examination.models import Examination
from apps.examination.serializers import ExaminationSerializer
from django.utils import timezone

class ExaminationService:

    @staticmethod
    def get_all():
        queryset = Examination.objects.all()
        serializer = ExaminationSerializer(queryset, many=True)
        return serializer.data

    @staticmethod
    def get_by_id(id: int):
        return get_object_or_404(Examination, pk=id)

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
    def lock(id: int):
        instance = get_object_or_404(Examination, pk=id)
        if not instance.is_lock:
            instance.is_lock = True
            instance.updated_at = timezone.now()
            instance.save(update_fields=["is_lock", "updated_at"])
        return instance

    @staticmethod
    def unlock(id: int):
        instance = get_object_or_404(Examination, pk=id)
        if instance.is_lock:
            instance.is_lock = False
            instance.updated_at = timezone.now()
            instance.save(update_fields=["is_lock", "updated_at"])
        return instance

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(Examination, pk=id)
        instance.status = Status.DELETED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["status", "updated_at"])

    @staticmethod
    def delete_by_examination_pack(examination_pack_id: int):
        return Examination.objects.filter(
            examination_pack_id=examination_pack_id,
            status=Status.ACTIVE
        ).update(status=Status.DELETED)