from dataclasses import asdict

from django.db import transaction
from rest_framework import serializers

from apps.common.serializers import BlankAsNullCharField
from apps.invoice.models import Invoice
from apps.order.models import Order

class InvoiceSerializer(serializers.ModelSerializer):
    qpay = serializers.SerializerMethodField()
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(), required=True
    )
    amount = serializers.DecimalField(
        max_digits=20, decimal_places=2, required=True
    )
    qpay_invoice_id = BlankAsNullCharField(max_length=100)

    def get_qpay(self, obj: Invoice) -> dict | None:
        # `qpay` is only attached in memory by InvoiceService.create; loaded invoices have none.
        qpay = getattr(obj, "qpay", None)
        if qpay:
            return asdict(qpay)
        return None

    class Meta:
        model = Invoice
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data) -> Invoice:
        request = self.context["request"]

        if request and not request.user.is_anonymous:
            validated_data["created_by"] = request.user
        else:
            validated_data["created_by"] = None

        return super().create(validated_data)