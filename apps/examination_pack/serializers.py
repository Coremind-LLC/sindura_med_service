from rest_framework import serializers

from apps.doctor.models import Doctor
from apps.examination_pack.models import ExaminationPack
from apps.examination_type.models import ExaminationType

class ExaminationPackSerializer(serializers.ModelSerializer):
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), required=True
    )
    examination_type = serializers.PrimaryKeyRelatedField(
        queryset=ExaminationType.objects.all(), required=True
    )
    doctor_first_name = serializers.CharField(source="doctor.first_name", read_only=True)
    doctor_last_name = serializers.CharField(source="doctor.last_name", read_only=True)
    doctor_position = serializers.CharField(source="doctor.position", read_only=True)
    examination_type_name = serializers.CharField(
        source="examination_type.name", read_only=True
    )

    class Meta:
        model = ExaminationPack
        fields = "__all__"
