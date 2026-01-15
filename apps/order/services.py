from django.shortcuts import get_object_or_404

from apps.common.enums import Status
from apps.order.models import Order
from apps.order.serializers import OrderSerializer

class OrderService:

    @staticmethod
    def get_all():
        queryset = Order.objects.all()
        serializer = OrderSerializer(queryset, many=True)
        return serializer.data

    @staticmethod
    def get_by_id(id: int):
        instance = get_object_or_404(Order, pk=id)
        serializer = OrderSerializer(instance)
        return serializer.data

    @staticmethod
    def create(data: dict, request):
        serializer = OrderSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def update(id: int, data: dict, request):
        instance = get_object_or_404(Order, pk=id)
        serializer = OrderSerializer(
            instance,
            data=data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(Order, pk=id)
        instance.status = Status.DELETED
        instance.save(update_fields=["status"])