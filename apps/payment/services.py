import logging

from django.db import transaction

from apps.examination.services import ExaminationService
from apps.invoice.enums import InvoiceStage
from apps.invoice.models import Invoice
from apps.invoice.services import InvoiceService
from apps.order.models import Order
from apps.order.services import OrderService
from apps.third_party.call_pro.services import CallProService
from apps.third_party.qpay.enums import PaymentStatus
from apps.third_party.qpay.models import PaymentPageResponse

logger = logging.getLogger(__name__)


class PaymentService:

    @staticmethod
    def is_paid(page: PaymentPageResponse) -> bool:
        """True when any payment row of a QPay check response is PAID."""
        return any(row.payment_status == PaymentStatus.PAID for row in page.rows)

    @staticmethod
    @transaction.atomic
    def approve(invoice: Invoice) -> Order | None:
        """Mark the invoice and its order paid and keep the booked examination locked.

        Returns None when a concurrent request (QPay callback vs. the app's polling) already
        approved this invoice, so the confirmation SMS is sent only once.
        """
        locked = Invoice.objects.select_for_update().get(pk=invoice.id)
        if locked.stage == InvoiceStage.PAID:
            return None
        InvoiceService.approve(invoice.id)
        order = OrderService.approve(invoice.order_id, None, None, True)
        if order.examination_id:
            ExaminationService.lock(order.examination_id)
        return order

    @staticmethod
    def notify(order: Order) -> None:
        """Send the booking confirmation SMS; failures are logged, never raised."""
        examination = order.examination
        if examination is None:
            return

        text = (
            f"Таны {examination.date} {examination.time} өдрийн захиалга баталгаажлаа. "
            f"Үзлэгийн дэлгэрэнгүй: {examination.examination_type.name} | {examination.room} өрөө. Синдура мед."
        )
        _, error = CallProService.send(order.phone, text)
        if error:
            logger.error(f"Failed to send confirmation SMS for order {order.id}: {error}")
