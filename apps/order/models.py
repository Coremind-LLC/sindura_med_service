from django.core.validators import MinLengthValidator
from django.db import models
from apps.common.models import BaseModel
from apps.examination.models import Examination
from apps.order.enums import OrderStage
from helpers.validator_helper import ValidatorHelper

class Order(BaseModel):
    first_name = models.CharField(max_length=32, validators=[MinLengthValidator(2)])
    last_name = models.CharField(max_length=32, validators=[MinLengthValidator(2)])
    register = models.CharField(max_length=10, validators=[MinLengthValidator(7)], null=True, blank=True)
    phone = models.CharField(max_length=8, validators=[ValidatorHelper.validate_phone, MinLengthValidator(8)])
    examination = models.ForeignKey(
        Examination, on_delete=models.PROTECT, null=True, blank=True
    )
    stage = models.CharField(
        choices=OrderStage.choices, max_length=20, default=OrderStage.PENDING
    )

    class Meta:
        db_table = "order"
