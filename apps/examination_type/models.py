from django.core.validators import MinLengthValidator
from django.db import models
from apps.common.models import BaseModel


class ExaminationType(BaseModel):
    name = models.CharField(max_length=255, validators=[MinLengthValidator(2)])

    class Meta:
        db_table = "examination_type"
