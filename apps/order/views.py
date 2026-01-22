from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.examination.services import ExaminationService
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

    def create(self, request, *args, **kwargs):
        order = OrderService.create(
            data=request.data,
            request=request
        )
        return Response(
            self.get_serializer(order).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="manual")
    def manual(self, request):
        order = OrderService.create_manual(
            data=request.data,
            request=request
        )
        return Response(
            self.get_serializer(order).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["patch"], url_path="approve")
    @transaction.atomic
    def approve(self, request, pk=None):
        order = OrderService.approve(pk)
        ExaminationService.lock(order.examination_id)

        return Response({"message": "Order approved"})

    @action(detail=True, methods=["patch"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, pk=None):
        order = OrderService.cancel(pk)
        ExaminationService.unlock(order.examination_id)

        return Response({"message": "Order cancelled"})