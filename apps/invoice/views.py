from typing import NoReturn

from rest_framework.exceptions import MethodNotAllowed

from apps.common.views import BaseViewSet
from apps.invoice.models import Invoice
from apps.invoice.serializers import InvoiceSerializer


class InvoiceViewSet(BaseViewSet):
    """Read-only invoice API for staff (project default DjangoModelPermissions).

    Invoices are created only by OrderService together with the QPay invoice and
    change stage only through the payment flow, so every write is disabled.
    """

    queryset = Invoice.objects.select_related("order")
    serializer_class = InvoiceSerializer

    def create(self, request, *args, **kwargs) -> NoReturn:
        raise MethodNotAllowed("POST", detail="Create is disabled for invoice")

    def update(self, request, *args, **kwargs) -> NoReturn:
        raise MethodNotAllowed("PUT", detail="Update is disabled for invoice")

    def partial_update(self, request, *args, **kwargs) -> NoReturn:
        raise MethodNotAllowed("PATCH", detail="Update is disabled for invoice")

    def destroy(self, request, *args, **kwargs) -> NoReturn:
        raise MethodNotAllowed("DELETE", detail="Delete is disabled for invoice")
