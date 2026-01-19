from celery import shared_task
from django.utils import timezone
from .models import Order
from apps.examination.services import ExaminationService

@shared_task
def check_order_stage(order_id):
    try:
        order = Order.objects.get(id=order_id)
        # Only update if still pending
        if order.stage == "PENDING":
            # Example: mark as expired
            order.stage = "EXPIRED"
            order.save()
            # Optional: unlock examination if needed
            ExaminationService.unlock(order.examination.id)
            print(f"Order {order.id} expired after 5 minutes")
        else:
            print(f"Order {order.id} already in stage {order.stage}")
    except Order.DoesNotExist:
        print(f"Order {order_id} does not exist")
