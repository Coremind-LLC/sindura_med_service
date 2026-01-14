from numbers import Number

from django.shortcuts import get_object_or_404

from apps.examination.models import Examination
from apps.examination.serializers import ExaminationSerializer

class ExaminationService:
    @staticmethod
    def get_all():
        queryset = Examination.objects.all()
        return ExaminationSerializer(queryset, many=True).data

    @staticmethod
    def get_by_id(id: Number):
        examination = get_object_or_404(Examination, pk=id)
        return ExaminationSerializer(examination).data

    @staticmethod
    def create(data: dict, request):
        serializer = ExaminationSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return ExaminationSerializer(instance).data

    @staticmethod
    def update(id: Number, data: dict, request):
        examination = get_object_or_404(Examination, pk=id)

        serializer = ExaminationSerializer(
            examination,
            data=data,
            partial=False,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return ExaminationSerializer(instance).data

    @staticmethod
    def delete(id: Number):
        examination = get_object_or_404(Examination, pk=id)
        examination.delete()