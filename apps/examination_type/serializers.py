from rest_framework import serializers
from apps.common.serializers import BlankAsNullCharField
from apps.examination_type.models import ExaminationType

class ExaminationTypeSerializer(serializers.ModelSerializer):
    icon = BlankAsNullCharField(max_length=255)

    class Meta:
        model = ExaminationType
        fields = "__all__"
