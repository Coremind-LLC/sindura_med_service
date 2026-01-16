from rest_framework import serializers

from apps.doctor.models import Doctor
from apps.examination.models import Examination
from apps.examination_type.models import ExaminationType

class ExaminationSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    updated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    date = serializers.DateField(required=True)
    time = serializers.TimeField(required=True)
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), required=True
    )
    examination_type = serializers.PrimaryKeyRelatedField(
        queryset=ExaminationType.objects.all(), required=True
    )
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, required=True)
    doctor_first_name = serializers.CharField(source="doctor.first_name", read_only=True)
    doctor_last_name = serializers.CharField(source="doctor.last_name", read_only=True)
    doctor_position = serializers.CharField(source="doctor.position", read_only=True)
    examination_type_name = serializers.CharField(
        source="examination_type.name", read_only=True
    )

    class Meta:
        model = Examination
        fields = "__all__"