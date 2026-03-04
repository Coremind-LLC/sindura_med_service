from django.db import transaction
from rest_framework import serializers

from apps.activity_log.enums import ActivityLogAction, ActivityLogModel
from apps.activity_log.services import ActivityLogService
from apps.examination.models import Examination
from apps.invoice.serializers import InvoiceSerializer
from apps.order.models import Order
from helpers.common_helper import CommonHelper

class OrderSerializer(serializers.ModelSerializer):
    register = serializers.CharField(
        required=True
    )
    examination = serializers.PrimaryKeyRelatedField(
        queryset=Examination.objects.all(), required=True
    )
    examination_total_amount = serializers.DecimalField(
        source="examination.total_amount", read_only=True, max_digits=20, decimal_places=2
    )
    examination_deposit_amount = serializers.DecimalField(
        source="examination.deposit_amount", read_only=True, max_digits=20, decimal_places=2
    )
    examination_type_id = serializers.IntegerField(source="examination.examination_type.id", read_only=True)
    examination_type_name = serializers.CharField(source="examination.examination_type.name", read_only=True)
    examination_type_icon = serializers.CharField(source="examination.examination_type.icon", read_only=True)
    examination_date = serializers.DateField(source="examination.date", read_only=True)
    examination_time = serializers.TimeField(source="examination.time", read_only=True)
    doctor_id = serializers.IntegerField(source="examination.doctor.id", read_only=True)
    doctor_first_name = serializers.CharField(source="examination.doctor.first_name", read_only=True)
    doctor_last_name = serializers.CharField(source="examination.doctor.last_name", read_only=True)
    invoice = InvoiceSerializer(read_only=True)

    class Meta:
        model = Order
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        examination = validated_data["examination"]

        if examination.is_lock:
            raise serializers.ValidationError({"examination": "Examination already locked"})

        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user

        order = super().create(validated_data)

        ActivityLogService.create(ActivityLogAction.CREATE,
                                  ActivityLogModel.ORDER,
                                  order.id,
                                  "Order created",
                                  CommonHelper.serialize_model(order),
                                  request.user)

        return order