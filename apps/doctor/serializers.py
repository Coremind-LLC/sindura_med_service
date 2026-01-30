from rest_framework import serializers
from apps.doctor.models import Doctor
from apps.doctor.services import DoctorService

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = "__all__"

    def validate_email(self, value):
        instance_id = self.instance.id if self.instance else None

        if DoctorService.exists_by_email(
            email=value,
            exclude_id=instance_id
        ):
            raise serializers.ValidationError("Email already exists")

        return value