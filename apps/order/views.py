from rest_framework.decorators import action
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

    # @action(detail=False, methods=["get"], url_path="(?P<order_id>\d+)/approve")
    # def approve(self, request, order_id):
