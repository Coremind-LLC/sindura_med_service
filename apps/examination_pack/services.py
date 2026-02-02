from datetime import date

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
    def search_by_dates(dates: list[str] | None = None):
        queryset = ExaminationPack.objects.filter(status=Status.ACTIVE)

        if dates:
            search_dates = [date.fromisoformat(d) for d in dates]
            queryset = queryset.filter(dates__overlap=search_dates)

        return queryset

    @staticmethod
    def exists_by_doctor(doctor_id: int) -> bool:
        return ExaminationPack.objects.filter(
            doctor_id=doctor_id,
            status=Status.ACTIVE
        ).exists()

    @staticmethod
    def exists_by_examination_type(examination_type_id: int) -> bool:
        return ExaminationPack.objects.filter(
            examination_type_id=examination_type_id,
            status=Status.ACTIVE
        ).exists()

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