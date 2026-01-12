from django.db import models


class InvoicePaymentCondition(models.TextChoices):
    CREDIT = "CREDIT", "Credit"
    CASH = "CASH", "Cash"


class InvoiceStage(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"
