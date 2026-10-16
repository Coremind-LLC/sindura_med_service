from rest_framework import serializers
from apps.common.serializers import BlankAsNullCharField, BlankAsNullEmailField
from apps.doctor.models import Doctor
from apps.doctor.services import DoctorService

class DoctorSerializer(serializers.ModelSerializer):
    image = BlankAsNullCharField(max_length=255)
    email = BlankAsNullEmailField(max_length=254)

    class Meta:
        model = Doctor
        fields = "__all__"

    def validate_email(self, value: str | None) -> str | None:
        instance_id = self.instance.id if self.instance else None

        if DoctorService.exists_by_email(
            email=value,
            exclude_id=instance_id
        ):
            raise serializers.ValidationError("Email already exists")

        return value