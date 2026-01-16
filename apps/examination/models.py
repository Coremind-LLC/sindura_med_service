from django.db import models
from apps.common.models import BaseModel
from apps.doctor.models import Doctor
from apps.examination_pack.models import ExaminationPack
from apps.examination_type.models import ExaminationType

class Examination(BaseModel):
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    examination_type = models.ForeignKey(
        ExaminationType, on_delete=models.PROTECT, null=True, blank=True
    )
    doctor = models.ForeignKey(
        Doctor, on_delete=models.PROTECT, null=True, blank=True
    )
    examination_pack = models.ForeignKey(
        ExaminationPack, on_delete=models.PROTECT, null=True, blank=True
    )
    is_lock = models.BooleanField(null=True, blank=True, default=False)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "examination"
