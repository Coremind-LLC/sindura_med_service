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
        if not isinstance(user, User):
            user = None

        return ActivityLog.objects.create(
            action=action,
            model=model,
            object_id=object_id,
            description=description,
            body=body,
            user=user,
            user_first_name=user.first_name if user else None,
            user_last_name=user.last_name if user else None
        )