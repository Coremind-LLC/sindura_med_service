from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.common.views import BaseViewSet
from apps.order.models import Order
from apps.order.serializers import OrderSerializer

class OrderViewSet(BaseViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]