from apps.common.views import BaseViewSet
from apps.order.models import Order
from apps.order.serializers import OrderSerializer

class OrderViewSet(BaseViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer