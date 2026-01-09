from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.common.enums import Status
from apps.user.managers import UserManager
from helpers.validator_helper import ValidatorHelper


class User(AbstractUser):
    username = None
    phone = models.CharField(max_length=8, validators=[ValidatorHelper.validate_phone])
    email = models.EmailField(unique=True)
    status = models.CharField(Status.choices, default=Status.ACTIVE)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone", "first_name", "last_name"]

    def clean(self):
        if not self.email and not self.phone:
            raise ValidationError({"message": "Either email or phone must be provided"})

    class Meta:
        db_table = "user"
        constraints = [
            models.UniqueConstraint(
                fields=["phone", "status"], name="unique_phone_status"
            ),
            models.UniqueConstraint(
                fields=["email", "status"], name="unique_email_status"
            ),
        ]
