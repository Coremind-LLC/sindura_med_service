from dataclasses import asdict

from django.db import transaction
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
    # created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    # updated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def get_qpay(self, obj: Invoice):
        if obj.qpay:
            return asdict(obj.qpay)
        return None

    class Meta:
        model = Invoice
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        if request and not request.user.is_anonymous:
            validated_data["created_by"] = request.user
        else:
            validated_data["created_by"] = None

        return super().create(validated_data)