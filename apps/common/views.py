from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.common.enums import Status
from apps.common.filters import BaseFilter
from apps.examination.models import Examination
from apps.order.services import OrderService
from apps.order.enums import OrderStage


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
                qs = qs.filter(status=Status.ACTIVE)
            if hasattr(model, "archived"):
                qs = qs.filter(archived=False)
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
        """Төлбөр төлөгдсөн захиалгын үзлэгийг, түгжээгүй ч гэсэн устгах боломжгүй байх"""
        model = self.queryset.model
        if model is Examination or (
            isinstance(model, type) and issubclass(model, Examination)
        ):
            if getattr(instance, "is_lock", False):
                raise ValidationError(
                    {"message": "Түгжээтэй үзлэгийг устгах боломжгүй"}
                )
        order = OrderService.get_by_examination(instance.id)
        if order and order.stage == OrderStage.PAID:
            raise ValidationError(
                {"message": "Төлбөр төлсөн захиалга байна, үзлэгийг устгах боломжгүй"}
            )
        if hasattr(instance, "updated_by"):
            instance.updated_by = self.request.user
        if hasattr(instance, "updated_at"):
            instance.updated_at = timezone.now()
        if hasattr(instance, "status"):
            instance.status = Status.DELETED
        instance.save()
