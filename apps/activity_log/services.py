import logging
from typing import Optional

from apps.activity_log.enums import ActivityLogModel, ActivityLogAction
from apps.activity_log.models import ActivityLog
from apps.user.models import User

logger = logging.getLogger(__name__)

class ActivityLogService:

    @staticmethod
    def create(action: ActivityLogAction,
               model: ActivityLogModel,
               object_id: Optional[int] = None,
               description: str = "",
               body: Optional[dict] = None,
               user: Optional[User] = None) -> ActivityLog:
        if user is not None and not isinstance(user, User):
            user = None

        return ActivityLog.objects.create(
            action=action,
            model=model,
            object_id=object_id,
            description=description,
            body=body,
            user=user
        )