from rest_framework import serializers
from apps.examination_type.models import ExaminationType

class ExaminationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExaminationType
        fields = "__all__"
