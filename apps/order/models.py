from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.db import models
from apps.common.models import BaseModel
from apps.examination.models import Examination
from apps.order.enums import OrderStage
from helpers.validator_helper import ValidatorHelper

class Order(BaseModel):
    first_name = models.CharField(max_length=32, validators=[MinLengthValidator(2)])
    last_name = models.CharField(max_length=32, validators=[MinLengthValidator(2)])
    register = models.CharField(max_length=12, validators=[MinLengthValidator(10)], null=True, blank=True)
    phone = models.CharField(max_length=8, validators=[ValidatorHelper.validate_phone, MinLengthValidator(8)])
    reason = models.TextField(null=True, blank=True)
    is_refund = models.BooleanField(default=False, null=True, blank=True)
    is_manual = models.BooleanField(default=False, null=True, blank=True)
    examination = models.ForeignKey(
        Examination, on_delete=models.PROTECT, null=True, blank=True
    )
    stage = models.CharField(
        choices=OrderStage.choices, max_length=20, default=OrderStage.PENDING
    )
    expire_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "order"
