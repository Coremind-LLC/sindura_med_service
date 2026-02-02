from rest_framework import serializers
from apps.activity_log.models import ActivityLog

class ActivityLogSerializer(serializers.ModelSerializer):
    action = serializers.CharField(required=True)
    model = serializers.CharField(required=True)
    object_id = serializers.IntegerField(required=True)
    description = serializers.CharField(required=True)

    class Meta:
        model = ActivityLog
        fields = "__all__"