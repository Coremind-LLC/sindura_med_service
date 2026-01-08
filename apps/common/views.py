from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.common.enums import Status
from apps.common.filters import BaseFilter


class BaseViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_class = BaseFilter
    ordering_fields = "__all__"
    ordering = ["-id"]

    def get_queryset(self):
        qs = super().get_queryset()
        model = self.queryset.model

        if self.action == "list":
            if hasattr(model, "status"):
                return qs.filter(status=Status.ACTIVE)
        return qs

    def perform_create(self, serializer):
        serializer.validated_data.pop("status", None)
        serializer.validated_data.pop("created_at", None)
        serializer.validated_data.pop("created_by", None)
        serializer.validated_data.pop("updated_at", None)
        serializer.validated_data.pop("updated_by", None)

        extra = {}
        if "created_by" in serializer.fields:
            extra["created_by"] = self.request.user
        serializer.save(**extra)

    def perform_update(self, serializer):
        serializer.validated_data.pop("status", None)
        serializer.validated_data.pop("created_at", None)
        serializer.validated_data.pop("created_by", None)
        serializer.validated_data.pop("updated_at", None)
        serializer.validated_data.pop("updated_by", None)

        extra = {}
        if "updated_by" in serializer.fields:
            extra["updated_by"] = self.request.user
        if "updated_at" in serializer.fields:
            extra["updated_at"] = timezone.now()
        serializer.save(**extra)

    def perform_destroy(self, instance):
        if hasattr(instance, "updated_by"):
            instance.updated_by = self.request.user
        if hasattr(instance, "updated_at"):
            instance.updated_at = timezone.now()
        if hasattr(instance, "status"):
            instance.status = Status.DELETED
        instance.save()
