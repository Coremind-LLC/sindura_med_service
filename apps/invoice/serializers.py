from rest_framework import serializers

from apps.invoice.models import Invoice
from apps.order.models import Order

class InvoiceSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(), required=True
    )

    class Meta:
        model = Invoice
        fields = "__all__"
