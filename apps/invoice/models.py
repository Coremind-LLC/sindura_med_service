from apps.common.models import BaseModel
from django.db import models
from apps.invoice.enums import InvoiceStage
from apps.order.models import Order


class Invoice(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=False, blank=False)
    stage = models.CharField(
        choices=InvoiceStage.choices, max_length=20, default=InvoiceStage.PENDING
    )
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    qpay_invoice_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "invoice"
