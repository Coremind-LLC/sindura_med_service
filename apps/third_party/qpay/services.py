import logging
from dataclasses import asdict, fields
from decimal import Decimal

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth
from rest_framework import status

from apps.third_party.qpay.enums import PaymentObjectType
from apps.third_party.qpay.models import (
    LoginResponse,
    InvoiceRequest,
    InvoiceResponse,
    PaymentRequest,
    PaymentOffsetRequest,
    PaymentPageResponse,
    PaymentResponse,
)
from config.settings import env
from helpers.number_helper import NumberHelper

logger = logging.getLogger(__name__)

_PAYMENT_RESPONSE_FIELDS = frozenset(field.name for field in fields(PaymentResponse))


def _payment_response(raw: dict) -> PaymentResponse:
    """Build a PaymentResponse, ignoring keys QPay sends that the dataclass does not model."""
    return PaymentResponse(**{key: value for key, value in raw.items() if key in _PAYMENT_RESPONSE_FIELDS})


class QPayService:

    @staticmethod
    def login() -> tuple[str | None, str | None]:
        try:
            response = requests.post(
                f"{env("QPAY_HOST")}/v2/auth/token",
                auth=HTTPBasicAuth(env("QPAY_USER"), env("QPAY_PASSWORD")),
                timeout=30,
            )

            if response.status_code != status.HTTP_200_OK:
                return None, response.text

            raw = response.json()
            raw.pop("not-before-policy", None)

            login_response = LoginResponse(**raw)

            return login_response.access_token, None
        except Exception as e:
            logger.exception(e)
            return None, str(e)

    @staticmethod
    def create_invoice(amount: Decimal, phone: str) -> tuple[InvoiceResponse | None, str | None]:
        data = InvoiceRequest(
            invoice_code=env("QPAY_INVOICE_CODE"),
            sender_invoice_no=str(NumberHelper.get_random_number(8)),
            invoice_receiver_code=phone,
            invoice_description=phone,
            sender_branch_code="01",
            amount=amount,
            callback_url=f"{settings.API_HOST}/payments/get_payment/",
        )

        data_dict = asdict(data)
        data_dict["amount"] = str(data_dict["amount"])

        token, error = QPayService.login()
        if error:
            logger.error(error)
            return None, error

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{env("QPAY_HOST")}/v2/invoice",
                headers=headers,
                json=data_dict,
                timeout=30,
            )

            if response.status_code != status.HTTP_200_OK:
                return None, response.text

            invoice_response = InvoiceResponse(**response.json())
            return invoice_response, None

        except Exception as e:
            logger.exception(e)
            return None, str(e)

    @staticmethod
    def check_payment(invoice_id: str) -> tuple[PaymentPageResponse | None, str | None]:
        data = PaymentRequest(
            object_type=PaymentObjectType.INVOICE,
            object_id=invoice_id,
            offset=PaymentOffsetRequest(page_number=1, page_limit=100),
        )

        token, error = QPayService.login()
        if error:
            logger.error(error)
            return None, error

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        data_dict = asdict(data)
        data_dict["object_type"] = data.object_type.value

        try:
            response = requests.post(
                f"{env("QPAY_HOST")}/v2/payment/check",
                headers=headers,
                json=data_dict,
                timeout=30,
            )

            if response.status_code != status.HTTP_200_OK:
                return None, response.text

            data = response.json()

            payment_page_response = PaymentPageResponse(
                count=data["count"],
                rows=[_payment_response(row) for row in data["rows"]],
                paid_amount=data.get("paid_amount"),
            )

            return payment_page_response, None
        except Exception as e:
            logger.exception(e)
            return None, str(e)

    @staticmethod
    def get_payment(payment_id: str) -> tuple[PaymentResponse | None, str | None]:
        token, error = QPayService.login()
        if error:
            logger.error(error)
            return None, error

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(
                f"{env("QPAY_HOST")}/v2/payment/{payment_id}",
                headers=headers,
                timeout=30,
            )

            if response.status_code != status.HTTP_200_OK:
                return None, response.json().get("message")

            payment_response = _payment_response(response.json())
            return payment_response, None
        except Exception as e:
            logger.exception(e)
            return None, str(e)
