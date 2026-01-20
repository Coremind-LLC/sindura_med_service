from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.examination.models import Examination
from apps.examination.services import ExaminationService
from apps.invoice.serializers import InvoiceSerializer
from apps.invoice.services import InvoiceService
from apps.order.models import Order
from apps.order.tasks import check_order_stage

class OrderSerializer(serializers.ModelSerializer):
    examination = serializers.PrimaryKeyRelatedField(
        queryset=Examination.objects.all(), required=True
    )
    examination_amount = serializers.DecimalField(
        source="examination.amount", read_only=True, max_digits=20, decimal_places=2
    )
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

        if request and not request.user.is_anonymous:
            validated_data["created_by"] = request.user
        else:
            validated_data["created_by"] = None

        validated_data["expire_at"] = timezone.now() + timedelta(minutes=1)

        order = super().create(validated_data)

        invoice, error = InvoiceService.create(order, request)
        if error:
            raise serializers.ValidationError({"invoice": f"Invoice creation failed: {error}"})

        ExaminationService.lock(order.examination.id)

        order.invoice = invoice

        check_order_stage.apply_async(args=(order.id, invoice.id), eta=order.expire_at)

        return order