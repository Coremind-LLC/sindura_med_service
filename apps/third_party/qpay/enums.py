from django.db import models


class PaymentStatus(models.TextChoices):
    NEW = "NEW", "New"
    FAILED = "FAILED", "Failed"
    PAID = "PAID", "Paid"
    PARTIAL = "PARTIAL", "Partial"
    REFUNDED = "REFUNDED", "Refunded"


class PaymentTransactionType(models.TextChoices):
    P2P = "P2P", "P2P"
    CARD = "CARD", "Card"


class PaymentObjectType(models.TextChoices):
    INVOICE = "INVOICE", "Invoice"
