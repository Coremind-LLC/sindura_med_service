import decimal
from dataclasses import dataclass
from typing import Optional

from apps.third_party.qpay.enums import (
    PaymentObjectType,
    PaymentTransactionType,
    PaymentStatus,
)


@dataclass
class LoginResponse:
    token_type: str
    refresh_expires_in: int
    refresh_token: str
    access_token: str
    expires_in: int
    scope: str
    session_state: str


@dataclass
class InvoiceRequest:
    invoice_code: str
    sender_invoice_no: str
    invoice_receiver_code: str
    invoice_description: str
    sender_branch_code: str
    amount: decimal.Decimal
    callback_url: str


@dataclass
class InvoiceUrlResponse:
    name: str
    description: str
    logo: str
    link: str


@dataclass
class InvoiceResponse:
    invoice_id: str
    qr_text: str
    qr_image: str
    qPay_shortUrl: str
    urls: list[InvoiceUrlResponse]


@dataclass
class PaymentOffsetRequest:
    page_number: int
    page_limit: int


@dataclass
class PaymentRequest:
    object_type: PaymentObjectType
    object_id: str
    offset: PaymentOffsetRequest


@dataclass
class PaymentP2PResponse:
    transaction_bank_code: str
    account_bank_code: str
    account_bank_name: str
    account_number: str
    status: str
    amount: str
    currency: str
    settlement_status: str


@dataclass
class PaymentCardResponse:
    card_merchant_code: str
    card_terminal_code: str
    card_number: str
    card_type: str
    is_cross_border: bool

    transaction_amount: str
    amount: str

    transaction_currency: str
    currency: str

    transaction_date: str
    date: str

    transaction_status: str
    status: str

    settlement_status: str
    settlement_status_date: str


@dataclass
class PaymentResponse:
    payment_id: Optional[str] = None
    payment_status: Optional[PaymentStatus] = None

    # Get
    payment_fee: Optional[str] = None
    # Check
    trx_fee: Optional[str] = None

    payment_amount: Optional[str] = None
    payment_currency: Optional[str] = None
    payment_date: Optional[str] = None
    payment_wallet: Optional[str] = None
    object_type: Optional[PaymentObjectType] = None
    object_id: Optional[str] = None
    next_payment_date: Optional[str] = None
    next_payment_datetime: Optional[str] = None

    # Get
    transaction_type: Optional[PaymentTransactionType] = None
    # Check
    payment_type: Optional[PaymentTransactionType] = None

    card_transactions: Optional[list[PaymentCardResponse]] = None
    p2p_transactions: Optional[list[PaymentP2PResponse]] = None


@dataclass
class PaymentPageResponse:
    count: int
    rows: list[PaymentResponse]
    paid_amount: Optional[decimal.Decimal] = None
