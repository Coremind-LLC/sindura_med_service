from dataclasses import asdict

from rest_framework import serializers

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
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    updated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def get_qpay(self, obj: Invoice):
        if obj.qpay:
            return asdict(obj.qpay)
        return None

    class Meta:
        model = Invoice
        fields = "__all__"