import django_filters
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import FieldError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, Field, OrderBy, F, QuerySet
from rest_framework.exceptions import ValidationError


class BaseFilter(django_filters.FilterSet):
    def get_filterset_fields(self) -> list[str]:
        model = getattr(self.queryset, "model", None)
        if not model:
            return []

        return [
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, Field) and not isinstance(field, ArrayField)
        ]

    def get_filterset_fields_override(self) -> list[str] | None:
        return None

    @property
    def filterset_fields(self) -> list[str]:
        override = self.get_filterset_fields_override()
        return override if override is not None else self.get_filterset_fields()

    def build_filters(self) -> Q:
        filters = Q()

        for field_name, search_value in self.request.query_params.items():
            if "." in field_name:
                related_field, field_name = field_name.split(".", 1)
                if related_field in self.filterset_fields:
                    filters &= Q(**{f"{related_field}__{field_name}": search_value})
            elif search_value and field_name in self.filterset_fields:
                filters &= Q(**{f"{field_name}__icontains": search_value})

        return filters

    def filter_queryset(self, queryset) -> QuerySet:
        # Unknown related lookups ("doctor.nope") or values of the wrong type
        # ("doctor.id=abc") are client errors, not server errors.
        try:
            queryset = queryset.filter(self.build_filters())
        except (FieldError, ValueError, DjangoValidationError) as err:
            raise ValidationError({"message": f"Invalid filter: {err}"}) from err

        sort_param = self.request.query_params.get("sort")
        if not sort_param:
            return queryset.order_by(OrderBy(F("id"), descending=True, nulls_last=True))

        field_name = sort_param.lstrip("-")
        try:
            # Resolve on a copy of the query so unknown fields fail here instead of at SQL time.
            F(field_name).resolve_expression(queryset.query.chain())
        except FieldError as err:
            raise ValidationError({"sort": f"Invalid sort field: {field_name}"}) from err

        order = OrderBy(F(field_name), descending=sort_param.startswith("-"), nulls_last=True)
        return queryset.order_by(order)
