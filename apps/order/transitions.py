from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers

from apps.activity_log.enums import ActivityLogAction, ActivityLogModel
from apps.activity_log.services import ActivityLogService
from apps.order.enums import OrderStage
from apps.order.models import Order
from apps.order.serializers import OrderTransitionSerializer
from apps.user.models import User
from helpers.common_helper import CommonHelper


class OrderTransitionService:
    """Order lookups and stage transitions shared by OrderService and the Celery tasks.

    Kept apart from apps.order.services so that apps.order.tasks does not have to
    import the module that enqueues its tasks.
    """

    @staticmethod
    def get_by_id(id: int) -> Order:
        return Order.objects.select_related("examination").get(pk=id)

    @staticmethod
    def apply_details(instance: Order, data: dict | None, user: User | None, update_fields: list[str]) -> None:
        """Copy the optional reason/refund data and the acting user onto the order.

        Only the keys present in ``data`` are changed, so an empty body is a valid request.
        """
        if data is not None:
            serializer = OrderTransitionSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            details = serializer.validated_data
            if "reason" in details:
                instance.reason = CommonHelper.blank_if_none(details["reason"])
                update_fields.append("reason")
            if "is_refund" in details:
                instance.is_refund = details["is_refund"]
                update_fields.append("is_refund")

        if user is not None:
            instance.updated_by = user
            update_fields.append("updated_by")

    @staticmethod
    def cancel(id: int, data: dict | None, user: User | None, is_task: bool) -> Order:
        instance = get_object_or_404(Order, pk=id)

        if not is_task:
            if instance.stage != OrderStage.PAID:
                raise serializers.ValidationError({"message": "Only paid orders can be cancelled"})

        update_fields = ["stage", "updated_at"]
        OrderTransitionService.apply_details(instance, data, user, update_fields)

        instance.stage = OrderStage.CANCELLED
        instance.updated_at = timezone.now()
        instance.save(update_fields=update_fields)

        ActivityLogService.create(ActivityLogAction.CANCEL,
                                  ActivityLogModel.ORDER,
                                  instance.id,
                                  "Order cancelled",
                                  CommonHelper.serialize_model(instance),
                                  user)

        return instance
