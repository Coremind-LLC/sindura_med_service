import logging

from django.utils import timezone
from celery import shared_task
from .enums import OrderStage
from .models import Order
from apps.examination.services import ExaminationService
from ..invoice.services import InvoiceService

logger = logging.getLogger(__name__)

@shared_task(
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5},
)
def check_order_stage(order_id, invoice_id):
    from .services import OrderService
    try:
        order = OrderService.get_by_id(order_id)

        if order.stage in (OrderStage.PAID, OrderStage.CANCELLED):
            return

        if order.expire_at and timezone.now() < order.expire_at:
            return

        InvoiceService.cancel(invoice_id)
        OrderService.cancel(order_id, None)
        ExaminationService.unlock(order.examination.id)

        logger.info(f"Order {order.id} expired and cancelled successfully.")
    except Order.DoesNotExist:
        logger.warning(f"Order {order_id} does not exist.")