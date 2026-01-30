import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from apps.common.enums import Status
from apps.doctor.models import Doctor

logger = logging.getLogger(__name__)

class DoctorService:

    @staticmethod
    def exists_by_email(email: str, exclude_id: int | None = None) -> bool:
        qs = Doctor.objects.filter(
            email__iexact=email,
            status=Status.ACTIVE
        )

        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        return qs.exists()

    @staticmethod
    def delete(id, user):
        doctor = get_object_or_404(Doctor, pk=id)

        doctor.status = Status.DELETED
        doctor.updated_at = timezone.now()
        doctor.updated_by = user
        doctor.save(update_fields=["status", "updated_at", "updated_by"])

        return doctor