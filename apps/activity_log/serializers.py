from rest_framework import serializers
from apps.activity_log.models import ActivityLog
from apps.common.serializers import BlankAsNullCharField

class ActivityLogSerializer(serializers.ModelSerializer):
    action = BlankAsNullCharField(required=True, allow_null=False, allow_blank=False)
    model = BlankAsNullCharField(required=True, allow_null=False, allow_blank=False)
    object_id = serializers.IntegerField(required=True)
    description = BlankAsNullCharField(required=True, allow_null=False, allow_blank=False)
    user_first_name = BlankAsNullCharField(max_length=100)
    user_last_name = BlankAsNullCharField(max_length=100)

    class Meta:
        model = ActivityLog
        fields = "__all__"