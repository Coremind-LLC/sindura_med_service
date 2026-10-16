from datetime import datetime
from typing import NoReturn

from django.db import transaction
from django.db.models import Sum, F, QuerySet
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle

from apps.common.views import BaseViewSet
from apps.examination.services import ExaminationService
from apps.order.models import Order
from apps.order.serializers import OrderPublicSerializer, OrderSerializer
from apps.order.services import OrderService

class OrderViewSet(BaseViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def is_public_lookup(self) -> bool:
        """Anonymous "my orders" page: list of paid orders by exact phone or register."""
        return self.action == "list" and not self.request.user.is_authenticated

    def get_permissions(self) -> list[BasePermission]:
        # Anonymous patients may book (create) and look up their own paid orders (list, limited
        # fields). Everything else needs a logged-in staff account, as before.
        if self.action == "create" or self.is_public_lookup():
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_throttles(self) -> list[BaseThrottle]:
        if self.is_public_lookup():
            self.throttle_scope = "order_lookup"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.is_public_lookup():
            return OrderPublicSerializer
        return super().get_serializer_class()

    def get_queryset(self) -> QuerySet[Order]:
        search = self.request.query_params.get("search", "").strip()

        if self.is_public_lookup():
            if not search:
                return Order.objects.none()
            return OrderService.lookup_paid(search)

        if search:
            return OrderService.search(search)

        return OrderService.get_all()

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request) -> Response | HttpResponse:
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response(
                {"message": "start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"message": "Date format must be YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        workbook = OrderService.export(start_date, end_date)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="orders_{start_date}_{end_date}.xlsx"'
        )

        workbook.save(response)
        return response

    def list(self, request, *args, **kwargs) -> Response:
        queryset = self.filter_queryset(self.get_queryset())

        totals = queryset.aggregate(
            total_amount_sum=Sum(F("examination__total_amount")),
            deposit_amount_sum=Sum(F("examination__deposit_amount"))
        )

        total_amount_sum = totals["total_amount_sum"] or 0
        deposit_amount_sum = totals["deposit_amount_sum"] or 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            paginated_data["total_amount_sum"] = total_amount_sum
            paginated_data["deposit_amount_sum"] = deposit_amount_sum
            return Response(paginated_data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "results": serializer.data,
            "total_amount_sum": total_amount_sum,
            "deposit_amount_sum": deposit_amount_sum
        })

    @action(detail=False, methods=["get"], url_path="report")
    def report(self, request) -> Response:
        start_date_str = self.request.query_params.get("start_date")
        end_date_str = self.request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return Response(
                {"message": "Start date and end date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"message": "Date must be in YYYY-MM-DD format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        response = OrderService.get_report(start_date, end_date)

        return Response({"results": response})



    def create(self, request, *args, **kwargs) -> Response:
        order = OrderService.create(
            data=request.data,
            request=request
        )
        return Response(
            self.get_serializer(order).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="manual")
    def manual(self, request) -> Response:
        order = OrderService.create_manual(
            data=request.data,
            request=request
        )
        return Response(
            self.get_serializer(order).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None, *args, **kwargs) -> Response:
        user = request.user if request.user.is_authenticated else None
        order = OrderService.update(pk, request.data, user)
        return Response(
            self.get_serializer(order).data,
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=["patch"], url_path="approve")
    @transaction.atomic
    def approve(self, request, pk=None) -> Response:
        order = OrderService.approve(pk, request.data, request.user, False)
        ExaminationService.lock(order.examination_id)

        return Response({"message": "Order approved"})

    @action(detail=True, methods=["patch"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, pk=None) -> Response:
        order = OrderService.cancel(pk, request.data, request.user, False)
        if order.examination_id:
            ExaminationService.unlock(order.examination_id)

        return Response({"message": "Order cancelled"})

    def destroy(self, request, *args, **kwargs) -> NoReturn:
        raise MethodNotAllowed("DELETE", detail="Delete is disabled for order")