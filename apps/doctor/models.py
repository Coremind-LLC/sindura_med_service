from django.core.validators import MinLengthValidator
from django.db import models
from apps.common.models import BaseModel


class Doctor(BaseModel):
    first_name = models.CharField(max_length=32, validators=[MinLengthValidator(2)])
    last_name = models.CharField(max_length=32, validators=[MinLengthValidator(2)])
    position = models.CharField(max_length=255, validators=[MinLengthValidator(2)])
    image = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "doctor"
