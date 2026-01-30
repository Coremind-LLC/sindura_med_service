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
        data["is_manual"] = False
        data["stage"] = OrderStage.PENDING
        data["expire_at"] = timezone.now() + timedelta(minutes=3)

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
        data["is_manual"] = True
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
    def update(id: int, data: dict):
        instance = get_object_or_404(Order, pk=id)

        examination = ExaminationService.get_by_id(data["examination"])

        if instance.examination.id != data["examination"]:
            if examination.is_lock:
                raise serializers.ValidationError({"message": "Examination already locked"})

            ExaminationService.lock(data["examination"])
            ExaminationService.unlock(instance.examination.id)

        instance.first_name = data["first_name"]
        instance.last_name = data["last_name"]
        instance.phone = data["phone"]
        instance.register = data["register"]
        instance.reason = data["reason"]
        instance.is_refund = data["is_refund"]
        instance.examination = examination
        instance.updated_at = timezone.now()
        instance.save(update_fields=["first_name", "last_name", "phone", "register", "reason", "is_refund", "examination", "updated_at"])
        return instance

    @staticmethod
    def approve(id: int, data: dict | None, is_task: bool):
        instance = get_object_or_404(Order, pk=id)

        if not is_task:
            if instance.stage != OrderStage.CANCELLED:
                raise serializers.ValidationError({"message": "Only cancelled orders can be approved"})

            if instance.examination.is_lock:
                raise serializers.ValidationError({"message": "Examination already locked"})

        update_fields = ["stage", "updated_at"]

        if data is not None:
            instance.reason = data["reason"]
            instance.is_refund = data["is_refund"]
            update_fields += ["reason", "is_refund"]

        instance.stage = OrderStage.PAID
        instance.updated_at = timezone.now()
        instance.save(update_fields=update_fields)
        return instance

    @staticmethod
    def cancel(id: int, data: dict | None, is_task: bool):
        instance = get_object_or_404(Order, pk=id)

        if not is_task:
            if instance.stage != OrderStage.PAID:
                raise serializers.ValidationError({"message": "Only paid orders can be cancelled"})

        update_fields = ["stage", "updated_at"]

        if data is not None:
            instance.reason = data["reason"]
            instance.is_refund = data["is_refund"]
            update_fields += ["reason", "is_refund"]

        instance.stage = OrderStage.CANCELLED
        instance.updated_at = timezone.now()
        instance.save(update_fields=update_fields)
        return instance

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(Order, pk=id)
        instance.status = Status.DELETED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["status", "updated_at"])