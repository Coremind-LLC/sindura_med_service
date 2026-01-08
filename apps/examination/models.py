from django.db import models
from apps.common.models import BaseModel
from apps.examination_type.models import ExaminationType

class Examination(BaseModel):
    examination_type = models.ForeignKey(
        ExaminationType, on_delete=models.PROTECT, null=True, blank=True
    )

    class Meta:
        db_table = "examination"
