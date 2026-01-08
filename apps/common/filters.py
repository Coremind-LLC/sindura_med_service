import django_filters
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q, Field, OrderBy, F


class BaseFilter(django_filters.FilterSet):
    def get_filterset_fields(self):
        model = getattr(self.queryset, "model", None)
        if not model:
            return []

        return [
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, Field) and not isinstance(field, ArrayField)
        ]

    def get_filterset_fields_override(self):
        return None

    @property
    def filterset_fields(self):
        override = self.get_filterset_fields_override()
        return override if override is not None else self.get_filterset_fields()

    def filter_queryset(self, queryset):
        search_terms = self.request.query_params
        filters = Q()

        for field_name, search_value in search_terms.items():
            if "." in field_name:
                related_field, field_name = field_name.split(".", 1)
                if related_field in self.filterset_fields:
                    filters &= Q(**{f"{related_field}__{field_name}": search_value})
            else:
                if search_value and field_name in self.filterset_fields:
                    filters &= Q(**{f"{field_name}__icontains": search_value})

        queryset = queryset.filter(filters)

        sort_param = search_terms.get("sort")
        if sort_param:
            descending = sort_param.startswith("-")
            field_name = sort_param.lstrip("-")

            order = OrderBy(F(field_name), descending=descending, nulls_last=True)
            queryset = queryset.order_by(order)
        else:
            queryset = queryset.order_by(
                OrderBy(F("id"), descending=True, nulls_last=True)
            )

        return queryset
