from datetime import datetime, date

from django.db import models
from django.forms.models import model_to_dict


class CommonHelper:

    @staticmethod
    def serialize_model(instance: models.Model) -> dict:
        data = model_to_dict(instance)

        for field in instance._meta.fields:
            value = getattr(instance, field.name)

            if isinstance(field, models.ForeignKey):
                data[field.name] = value.id if value else None

            elif isinstance(value, (datetime, date)):
                data[field.name] = value.isoformat()

        return data