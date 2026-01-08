from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
import re


class ValidatorHelper:
    @staticmethod
    def validate_phone(value):
        if not value.isdigit():
            raise ValidationError("Phone number must only contain digits.")
        if len(value) != 8:
            raise ValidationError("Phone number must be exactly 8 digits long.")

    @staticmethod
    def is_valid_phone(value):
        return value.isdigit() and len(value) == 8

    @staticmethod
    def is_valid_email(value):
        validator = EmailValidator()
        try:
            validator(value)
            return True
        except ValidationError:
            return False

    @staticmethod
    def is_valid_register(value):
        if len(value) == 7:
            return value.isdigit()
        elif len(value) == 10:
            return re.match(r"^[\u0400-\u04FF]{2}\d+$", value) is not None
        return False
