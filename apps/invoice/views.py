from rest_framework.exceptions import MethodNotAllowed

from apps.common.views import BaseViewSet
from apps.invoice.models import Invoice
from apps.invoice.serializers import InvoiceSerializer


class InvoiceViewSet(BaseViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT", detail="Update is disabled for invoice")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PATCH", detail="Update is disabled for invoice")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Delete is disabled for invoice")
