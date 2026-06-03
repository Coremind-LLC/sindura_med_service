import logging
from datetime import timedelta, date

from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from openpyxl import Workbook
from rest_framework import serializers

from apps.activity_log.enums import ActivityLogAction, ActivityLogModel
from apps.activity_log.services import ActivityLogService
from apps.common.enums import Status
from apps.examination.services import ExaminationService
from apps.invoice.services import InvoiceService
from apps.order.enums import OrderStage
from apps.order.models import Order
from apps.order.serializers import OrderSerializer
from django.utils import timezone

from apps.order.tasks import check_order_stage
from apps.user.models import User
from helpers.common_helper import CommonHelper

logger = logging.getLogger(__name__)


class OrderService:

    @staticmethod
    def get_all():
        return Order.objects.filter(status=Status.ACTIVE)

    @staticmethod
    def search(value: str):
        return OrderService.get_all().filter(
            Q(phone__icontains=value) | Q(register__icontains=value)
        )

    @staticmethod
    def get_by_id(id: int) -> Order:
        return Order.objects.select_related("examination").get(pk=id)

    @staticmethod
    def get_report(start_date: date, end_date: date):
        return (
            Order.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
                status=Status.ACTIVE,
            )
            .values("stage")
            .annotate(
                count=Count("id"),
                deposit_amount=Sum(
                    "examination__deposit_amount", filter=Q(stage=OrderStage.PAID)
                ),
            )
        )

    @staticmethod
    def export(start_date: date, end_date: date):
        orders = Order.objects.filter(
            stage__in=[OrderStage.CANCELLED, OrderStage.PAID],
            status=Status.ACTIVE,
            created_at__date__range=(start_date, end_date),
        ).order_by("-id")

        wb = Workbook()
        ws = wb.active
        ws.title = "Захиалга"

        ws.append(
            [
                "ID",
                "Овог",
                "Нэр",
                "Регистр",
                "Утас",
                "Тайлбар",
                "Үзлэгийн төрөл",
                "Өдөр цаг",
                "Урьдчилгаа төлбөр",
                "Нийт дүн",
                "Төлөв",
                "Гараас үүсгэсэн эсэх",
                "Буцаалт хийсэн эсэх",
                "Үүсгэсэн огноо",
                "Шинэчилсэн огноо",
            ]
        )

        for order in orders:
            ws.append(
                [
                    order.id,
                    order.last_name,
                    order.first_name,
                    order.register,
                    order.phone,
                    order.reason,
                    order.examination.examination_type.name,
                    f"{order.examination.date} {order.examination.time}",
                    order.examination.deposit_amount,
                    order.examination.total_amount,
                    (
                        "Цуцалсан"
                        if order.stage == OrderStage.CANCELLED
                        else "Төлөгдсөн" if order.stage == OrderStage.PAID else ""
                    ),
                    (
                        "Тийм"
                        if order.is_manual is True
                        else "Үгүй" if order.is_manual is False else ""
                    ),
                    (
                        "Тийм"
                        if order.is_refund is True
                        else "Үгүй" if order.is_refund is False else ""
                    ),
                    (
                        order.created_at.strftime("%Y-%m-%d %H:%M")
                        if order.created_at
                        else ""
                    ),
                    (
                        order.updated_at.strftime("%Y-%m-%d %H:%M")
                        if order.updated_at
                        else ""
                    ),
                ]
            )

        return wb

    @staticmethod
    def create(data: dict, request):
        data["is_manual"] = False
        data["stage"] = OrderStage.PENDING
        data["expire_at"] = timezone.now() + timedelta(minutes=3)

        serializer = OrderSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        invoice, error = InvoiceService.create(order, request)
        if error:
            raise serializers.ValidationError(
                {"invoice": f"Invoice creation failed: {error}"}
            )

        ExaminationService.lock(order.examination.id)

        order.invoice = invoice

        check_order_stage.apply_async(args=(order.id, invoice.id), eta=order.expire_at)

        return order

    @staticmethod
    def create_manual(data: dict, request):
        data["is_manual"] = True
        data["stage"] = OrderStage.PAID

        serializer = OrderSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        ExaminationService.lock(order.examination.id)

        return order

    @staticmethod
    def update(id: int, data: dict, user: User | None):
        instance = get_object_or_404(Order, pk=id)

        examination = ExaminationService.get_by_id(data["examination"])

        if instance.examination.id != data["examination"]:
            if examination.is_lock:
                raise serializers.ValidationError(
                    {"message": "Examination already locked"}
                )

            ExaminationService.lock(data["examination"])
            ExaminationService.unlock(instance.examination.id)

        update_fields = [
            "first_name",
            "last_name",
            "phone",
            "register",
            "reason",
            "is_refund",
            "examination",
            "updated_at",
        ]

        if user is not None:
            instance.updated_by = user
            update_fields += ["updated_by"]

        instance.first_name = data["first_name"]
        instance.last_name = data["last_name"]
        instance.phone = data["phone"]
        instance.register = data["register"]
        instance.reason = data["reason"]
        instance.is_refund = data["is_refund"]
        instance.examination = examination
        instance.updated_at = timezone.now()
        instance.save(update_fields=update_fields)

        ActivityLogService.create(
            ActivityLogAction.UPDATE,
            ActivityLogModel.ORDER,
            instance.id,
            f"Order updated.",
            CommonHelper.serialize_model(instance),
        )

        return instance

    @staticmethod
    def approve(id: int, data: dict | None, user: User | None, is_task: bool):
        instance = get_object_or_404(Order, pk=id)

        if not is_task:
            if instance.stage != OrderStage.CANCELLED:
                raise serializers.ValidationError(
                    {"message": "Only cancelled orders can be approved"}
                )

            if instance.examination.is_lock:
                raise serializers.ValidationError(
                    {"message": "Examination already locked"}
                )

        update_fields = ["stage", "updated_at"]

        if data is not None:
            instance.reason = data["reason"]
            instance.is_refund = data["is_refund"]
            update_fields += ["reason", "is_refund"]

        if user is not None:
            instance.updated_by = user
            update_fields += ["updated_by"]

        instance.stage = OrderStage.PAID
        instance.updated_at = timezone.now()
        instance.updated_by = user
        instance.save(update_fields=update_fields)

        ActivityLogService.create(
            ActivityLogAction.APPROVE,
            ActivityLogModel.ORDER,
            instance.id,
            "Order approved",
            CommonHelper.serialize_model(instance),
            user,
        )

        return instance

    @staticmethod
    def cancel(id: int, data: dict | None, user: User | None, is_task: bool):
        instance = get_object_or_404(Order, pk=id)

        if not is_task:
            if instance.stage != OrderStage.PAID:
                raise serializers.ValidationError(
                    {"message": "Only paid orders can be cancelled"}
                )

        update_fields = ["stage", "updated_at"]

        if data is not None:
            instance.reason = data["reason"]
            instance.is_refund = data["is_refund"]
            update_fields += ["reason", "is_refund"]

        if user is not None:
            instance.updated_by = user
            update_fields += ["updated_by"]

        instance.stage = OrderStage.CANCELLED
        instance.updated_at = timezone.now()
        instance.save(update_fields=update_fields)

        ActivityLogService.create(
            ActivityLogAction.CANCEL,
            ActivityLogModel.ORDER,
            instance.id,
            f"Order cancelled",
            CommonHelper.serialize_model(instance),
            user,
        )

        return instance

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(Order, pk=id)
        instance.status = Status.DELETED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["status", "updated_at"])

    @staticmethod
    def get_by_examination(examination_id: int):
        try:
            order = Order.objects.get(examination_id=examination_id)
            return order
        except Order.DoesNotExist:
            return None
        except Exception:
            return None
