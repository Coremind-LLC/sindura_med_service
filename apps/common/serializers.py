from typing import Any

from rest_framework import serializers
from rest_framework.fields import empty


class BlankAsNullCharField(serializers.CharField):
    """CharField for model columns that store "" instead of NULL.

    The API stays backward compatible with the old nullable columns: ``null`` is
    accepted on input and stored as "", and "" is rendered back as ``null``.
    """

    def __init__(self, **kwargs: Any) -> None:
        if not kwargs.get("read_only"):
            kwargs.setdefault("allow_null", True)
            kwargs.setdefault("allow_blank", True)
            kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def run_validation(self, data: Any = empty) -> Any:
        value = super().run_validation(data)
        return "" if value is None else value

    def to_representation(self, value: Any) -> str | None:
        if value == "":
            return None
        return super().to_representation(value)


class BlankAsNullEmailField(BlankAsNullCharField, serializers.EmailField):
    """EmailField variant of BlankAsNullCharField (validates non-empty values as emails)."""
