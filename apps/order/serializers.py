from django.db import transaction
from rest_framework import serializers

from apps.examination.models import Examination
from apps.invoice.serializers import InvoiceSerializer
from apps.order.models import Order


class OrderSerializer(serializers.ModelSerializer):
    examination = serializers.PrimaryKeyRelatedField(
        queryset=Examination.objects.all(), required=True
    )
    examination_total_amount = serializers.DecimalField(
        source="examination.total_amount", read_only=True, max_digits=20, decimal_places=2
    )
    examination_deposit_amount = serializers.DecimalField(
        source="examination.deposit_amount", read_only=True, max_digits=20, decimal_places=2
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

        return super().create(validated_data)