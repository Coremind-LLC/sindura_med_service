from __future__ import annotations

import logging
from datetime import timedelta, date, datetime

from django.db import transaction
from django.db.models import Q, Count, Sum, QuerySet
from django.shortcuts import get_object_or_404
from openpyxl import Workbook
from rest_framework import serializers
from rest_framework.request import Request

from apps.activity_log.enums import ActivityLogAction, ActivityLogModel
from apps.activity_log.services import ActivityLogService
from apps.common.enums import Status
from apps.examination.models import Examination
from apps.examination.services import ExaminationService
from apps.invoice.services import InvoiceService
from apps.order.enums import OrderStage
from apps.order.models import Order
from apps.order.serializers import OrderSerializer, OrderUpdateSerializer
from django.utils import timezone

from apps.order.tasks import check_order_stage
from apps.order.transitions import OrderTransitionService
from apps.user.models import User
from helpers.common_helper import CommonHelper

logger = logging.getLogger(__name__)

EXPORT_HEADERS = [
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
    "Шинэчилсэн огноо"
]

EXPORT_STAGE_LABELS = {
    OrderStage.CANCELLED: "Цуцалсан",
    OrderStage.PAID: "Төлөгдсөн",
}


def _yes_no(value: bool | None) -> str:
    return "Тийм" if value is True else "Үгүй" if value is False else ""


def _format_datetime(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else ""


def _export_row(order: Order) -> list:
    examination = order.examination
    return [
        order.id,
        order.last_name,
        order.first_name,
        order.register,
        order.phone,
        order.reason,
        examination.examination_type.name,
        f"{examination.date} {examination.time}",
        examination.deposit_amount,
        examination.total_amount,
        EXPORT_STAGE_LABELS.get(order.stage, ""),
        _yes_no(order.is_manual),
        _yes_no(order.is_refund),
        _format_datetime(order.created_at),
        _format_datetime(order.updated_at)
    ]


class OrderService:

    @staticmethod
    def get_all() -> QuerySet[Order]:
        return Order.objects.filter(status=Status.ACTIVE)

    @staticmethod
    def lookup_paid(value: str) -> QuerySet[Order]:
        """Paid orders whose phone or register is exactly `value` (public "my orders" lookup)."""
        return OrderService.get_all().filter(
            Q(phone=value) | Q(register__iexact=value),
            stage=OrderStage.PAID,
        )

    @staticmethod
    def search(value: str) -> QuerySet[Order]:
        return OrderService.get_all().filter(
            Q(phone__icontains=value) |
            Q(register__icontains=value)
        )

    @staticmethod
    def get_by_id(id: int) -> Order:
        return OrderTransitionService.get_by_id(id)

    @staticmethod
    def get_report(start_date: date, end_date: date) -> QuerySet[Order, dict]:
        return (Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status=Status.ACTIVE
        )
            .values("stage")
            .annotate(
                count=Count("id"),
                deposit_amount=Sum(
                    "examination__deposit_amount",
                    filter=Q(stage=OrderStage.PAID)
                )
            )
        )

    @staticmethod
    def export(start_date: date, end_date: date) -> Workbook:
        orders = Order.objects.filter(
            stage__in=[OrderStage.CANCELLED, OrderStage.PAID],
            status=Status.ACTIVE,
            created_at__date__range=(start_date, end_date)
        ).order_by("-id")

        wb = Workbook()
        ws = wb.active
        ws.title = "Захиалга"

        ws.append(EXPORT_HEADERS)

        for order in orders:
            ws.append(_export_row(order))

        return wb

    @staticmethod
    def create(data: dict, request: Request) -> Order:
        data["is_manual"] = False
        data["stage"] = OrderStage.PENDING
        data["expire_at"] = timezone.now() + timedelta(minutes=3)

        # One transaction: a QPay failure must leave no order, invoice or locked examination.
        with transaction.atomic():
            order = OrderService._save_new(data, request)

            invoice, error = InvoiceService.create(order, request)
            if error:
                raise serializers.ValidationError({"invoice": f"Invoice creation failed: {error}"})

            order.invoice = invoice

            # Only schedule the expiry check once the order is really in the database.
            transaction.on_commit(
                lambda: check_order_stage.apply_async(args=(order.id, invoice.id), eta=order.expire_at)
            )

        return order

    @staticmethod
    def create_manual(data: dict, request: Request) -> Order:
        data["is_manual"] = True
        data["stage"] = OrderStage.PAID

        with transaction.atomic():
            return OrderService._save_new(data, request)

    @staticmethod
    def _save_new(data: dict, request: Request) -> Order:
        """Validate and save a new order and lock its examination (caller owns the transaction)."""
        examination_id = str(data.get("examination", ""))
        if examination_id.isdigit():
            # Row lock: a concurrent booking of the same slot waits here, then sees is_lock=True.
            Examination.objects.select_for_update().filter(pk=examination_id).first()
        serializer = OrderSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        ExaminationService.lock(order.examination.id)

        return order

    @staticmethod
    def _move_examination(instance: Order, examination: Examination) -> None:
        """Lock the new examination and free the old one when an order is moved."""
        if instance.examination_id == examination.id:
            return

        if examination.is_lock:
            raise serializers.ValidationError({"message": "Examination already locked"})

        ExaminationService.lock(examination.id)
        if instance.examination_id:
            ExaminationService.unlock(instance.examination_id)

    @staticmethod
    @transaction.atomic
    def update(id: int, data: dict, user: User | None) -> Order:
        instance = get_object_or_404(Order, pk=id)

        serializer = OrderUpdateSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        examination = validated["examination"]
        OrderService._move_examination(instance, examination)

        update_fields = ["first_name", "last_name", "phone", "register", "reason", "is_refund", "examination",
                         "updated_at"]

        if user is not None:
            instance.updated_by = user
            update_fields += ["updated_by"]

        instance.first_name = validated["first_name"]
        instance.last_name = validated["last_name"]
        instance.phone = validated["phone"]
        instance.register = CommonHelper.blank_if_none(validated.get("register", instance.register))
        instance.reason = CommonHelper.blank_if_none(validated.get("reason", instance.reason))
        instance.is_refund = validated.get("is_refund", instance.is_refund)
        instance.examination = examination
        instance.updated_at = timezone.now()
        instance.save(update_fields=update_fields)

        ActivityLogService.create(ActivityLogAction.UPDATE,
                                  ActivityLogModel.ORDER,
                                  instance.id,
                                  "Order updated.",
                                  CommonHelper.serialize_model(instance))

        return instance

    @staticmethod
    def approve(id: int, data: dict | None, user: User | None, is_task: bool) -> Order:
        instance = get_object_or_404(Order, pk=id)

        if not is_task:
            if instance.stage != OrderStage.CANCELLED:
                raise serializers.ValidationError({"message": "Only cancelled orders can be approved"})

            if instance.examination is None:
                raise serializers.ValidationError({"examination": "Order has no examination"})

            if instance.examination.is_lock:
                raise serializers.ValidationError({"message": "Examination already locked"})

        update_fields = ["stage", "updated_at"]
        OrderTransitionService.apply_details(instance, data, user, update_fields)

        instance.stage = OrderStage.PAID
        instance.updated_at = timezone.now()
        instance.updated_by = user
        instance.save(update_fields=update_fields)

        ActivityLogService.create(ActivityLogAction.APPROVE,
                                  ActivityLogModel.ORDER,
                                  instance.id,
                                  "Order approved",
                                  CommonHelper.serialize_model(instance),
                                  user)

        return instance

    @staticmethod
    def cancel(id: int, data: dict | None, user: User | None, is_task: bool) -> Order:
        return OrderTransitionService.cancel(id, data, user, is_task)

    @staticmethod
    def delete(id: int) -> None:
        instance = get_object_or_404(Order, pk=id)
        instance.status = Status.DELETED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["status", "updated_at"])