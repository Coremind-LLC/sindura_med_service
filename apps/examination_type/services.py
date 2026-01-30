import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from apps.common.enums import Status
from apps.examination_type.models import ExaminationType

logger = logging.getLogger(__name__)

class ExaminationTypeService:

    @staticmethod
    def delete(id, user):
        examination_type = get_object_or_404(ExaminationType, pk=id)

        examination_type.status = Status.DELETED
        examination_type.updated_at = timezone.now()
        examination_type.updated_by = user
        examination_type.save(update_fields=["status", "updated_at", "updated_by"])

        return examination_type