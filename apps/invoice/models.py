from apps.common.models import BaseModel
from django.db import models
from apps.invoice.enums import InvoicePaymentCondition, InvoiceStage
from apps.order.models import Order
from apps.third_party.qpay.models import InvoiceResponse


class Invoice(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=False, blank=False)
    payment_condition = models.CharField(
        choices=InvoicePaymentCondition.choices,
        max_length=20,
        null=True,
        blank=True,
    )
    stage = models.CharField(
        choices=InvoiceStage.choices, max_length=20, default=InvoiceStage.PENDING
    )

    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    qpay_invoice_id = models.CharField(max_length=100, null=True, blank=True)

    _qpay: InvoiceResponse | None = None

    @property
    def qpay(self) -> InvoiceResponse | None:
        return self._qpay

    @qpay.setter
    def qpay(self, value: InvoiceResponse):
        self._qpay = value

    class Meta:
        db_table = "invoice"
