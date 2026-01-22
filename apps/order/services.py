import logging
from datetime import timedelta

from django.shortcuts import get_object_or_404
from rest_framework import serializers

from apps.common.enums import Status
from apps.examination.services import ExaminationService
from apps.invoice.services import InvoiceService
from apps.order.enums import OrderStage
from apps.order.models import Order
from apps.order.serializers import OrderSerializer
from django.utils import timezone

from apps.order.tasks import check_order_stage

logger = logging.getLogger(__name__)

class OrderService:

    @staticmethod
    def get_all():
        queryset = Order.objects.all()
        serializer = OrderSerializer(queryset, many=True)
        return serializer.data

    @staticmethod
    def get_by_id(id: int) -> Order:
        return Order.objects.select_related("examination").get(pk=id)

    @staticmethod
    def create(data: dict, request):
        data["stage"] = OrderStage.PENDING
        data["expire_at"] = timezone.now() + timedelta(minutes=5)

        serializer = OrderSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        invoice, error = InvoiceService.create(order, request)
        if error:
            raise serializers.ValidationError({"invoice": f"Invoice creation failed: {error}"})

        ExaminationService.lock(order.examination.id)

        order.invoice = invoice

        check_order_stage.apply_async(args=(order.id, invoice.id), eta=order.expire_at)

        return order

    @staticmethod
    def create_manual(data: dict, request):
        data["stage"] = OrderStage.PAID

        serializer = OrderSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        ExaminationService.lock(order.examination.id)

        return order

    @staticmethod
    def update(id: int, data: dict, request):
        instance = get_object_or_404(Order, pk=id)
        serializer = OrderSerializer(
            instance,
            data=data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def approve(id: int):
        instance = get_object_or_404(Order, pk=id)

        if instance.stage == OrderStage.PAID:
            return instance

        instance.stage = OrderStage.PAID
        instance.updated_at = timezone.now()
        instance.save(update_fields=["stage", "updated_at"])
        return instance

    @staticmethod
    def cancel(id: int):
        instance = get_object_or_404(Order, pk=id)

        if instance.stage == OrderStage.CANCELLED:
            return instance

        instance.stage = OrderStage.CANCELLED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["stage", "updated_at"])
        return instance

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(Order, pk=id)
        instance.status = Status.DELETED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["status", "updated_at"])