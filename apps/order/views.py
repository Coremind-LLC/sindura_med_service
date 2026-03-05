from datetime import datetime

from django.db import transaction
from django.db.models import Sum, F
from django.http import HttpResponse
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

    def get_queryset(self):
        search = self.request.query_params.get("search", "").strip()

        if search:
            return OrderService.search(search)

        return OrderService.get_all()

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
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

    def list(self, request, *args, **kwargs):
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
    def report(self, request):
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

    def update(self, request, pk=None, *args, **kwargs):
        user = request.user if request.user.is_authenticated else None
        order = OrderService.update(pk, request.data, user)
        return Response(
            self.get_serializer(order).data,
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=["patch"], url_path="approve")
    @transaction.atomic
    def approve(self, request, pk=None):
        order = OrderService.approve(pk, request.data, request.user, False)
        ExaminationService.lock(order.examination_id)

        return Response({"message": "Order approved"})

    @action(detail=True, methods=["patch"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, pk=None):
        order = OrderService.cancel(pk, request.data, request.user, False)
        ExaminationService.unlock(order.examination_id)

        return Response({"message": "Order cancelled"})

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Delete is disabled for order")