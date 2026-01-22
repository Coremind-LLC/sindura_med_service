from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.order.models import Order
from apps.order.serializers import OrderSerializer
from apps.order.services import OrderService

class OrderViewSet(BaseViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.action in ["create", "list"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT", detail="Update is disabled for order")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Delete is disabled for order")

    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     order = serializer.save()
    #     return Response(self.get_serializer(order).data)

    # @action(detail=True, methods=["patch"], url_path="approve")
    # def approve(self, request, pk=None):
    #     order = self.get_object()
    #     order, error = OrderService.approve(order.id)
    #     if error:
    #         return Response({"message": error}, status=400)
    #     return Response({"message": "Order approved"})
    #
    # @action(detail=True, methods=["patch"], url_path="cancel")
    # def cancel(self, request, pk=None):
    #     order = self.get_object()
    #     order, error = OrderService.cancel(order.id)
    #     if error:
    #         return Response({"message": error}, status=400)
    #     return Response({"message": "Order cancelled"})
    #
    # @action(detail=False, methods=["post"], url_path="manual")
    # def manual(self, request):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     order = serializer.save()
    #     return Response(self.get_serializer(order).data)

