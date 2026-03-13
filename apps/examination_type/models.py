from django.core.validators import MinLengthValidator
from django.db import models
from apps.common.models import BaseModel


class ExaminationType(BaseModel):
    name = models.CharField(max_length=255, validators=[MinLengthValidator(2)])
    icon = models.CharField(max_length=255, null=True, blank=True)
    archived = models.BooleanField(default=False)


    class Meta:
        db_table = "examination_type"
        ordering = ["-id"]