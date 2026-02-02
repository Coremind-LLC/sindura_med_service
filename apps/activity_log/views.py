from apps.activity_log.models import ActivityLog
from apps.activity_log.serializers import ActivityLogSerializer
from apps.common.views import BaseViewSet

class ActivityLogViewSet(BaseViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer