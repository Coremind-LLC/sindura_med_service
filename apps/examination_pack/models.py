from django.contrib.postgres.fields import ArrayField
from django.db import models
from apps.common.models import BaseModel
from apps.doctor.models import Doctor
from apps.examination_type.models import ExaminationType

class ExaminationPack(BaseModel):
    dates = ArrayField(base_field=models.DateField())
    start_time = models.TimeField()
    end_time = models.TimeField()
    lunch_break_start_time = models.TimeField(null=True, blank=True)
    lunch_break_end_time = models.TimeField(null=True, blank=True)
    examination_type = models.ForeignKey(
        ExaminationType, on_delete=models.PROTECT, null=True, blank=True
    )
    doctor = models.ForeignKey(
        Doctor, on_delete=models.PROTECT, null=True, blank=True
    )
    period = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "examination_pack"
