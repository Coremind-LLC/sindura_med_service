import logging

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