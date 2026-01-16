from rest_framework import serializers

from apps.invoice.models import Invoice
from apps.order.models import Order

class InvoiceSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(), required=True
    )
    amount = serializers.DecimalField(
        max_digits=20, decimal_places=2, required=True
    )
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    updated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Invoice
        fields = "__all__"
