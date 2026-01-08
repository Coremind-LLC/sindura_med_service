from rest_framework import serializers
from apps.examination.models import Examination

class ExaminationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Examination
        fields = "__all__"
