from django.db import models

from apps.activity_log.enums import ActivityLogAction
from apps.common.models import BaseModel
from apps.user.models import User

class ActivityLog(BaseModel):
    action = models.CharField(max_length=10, choices=ActivityLogAction.choices)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "activity_log"
        ordering = ["-id"]