"""Shared builders for the test suite. Keep per-app tests short by creating data here."""
import datetime
from decimal import Decimal
from itertools import count

from rest_framework.test import APITestCase

from apps.doctor.models import Doctor
from apps.examination.models import Examination
from apps.examination_pack.models import ExaminationPack
from apps.examination_type.models import ExaminationType
from apps.invoice.models import Invoice
from apps.order.models import Order
from apps.user.models import User

_seq = count(1)

TEST_PASSWORD = "pass-for-tests-1"


def make_user(superuser=False, **fields):
    n = next(_seq)
    data = {
        "email": f"user{n}@example.com",
        "phone": f"{88000000 + n}",
        "first_name": "Bat",
        "last_name": "Dorj",
        "password": TEST_PASSWORD,
    }
    data.update(fields)
    create = User.objects.create_superuser if superuser else User.objects.create_user
    return create(**data)


def make_doctor(**fields):
    data = {"first_name": "Sarnai", "last_name": "Bold", "position": "Surgeon"}
    data.update(fields)
    return Doctor.objects.create(**data)


def make_examination_type(**fields):
    data = {"name": "Ultrasound"}
    data.update(fields)
    return ExaminationType.objects.create(**data)


def make_examination_pack(**fields):
    data = {
        "dates": [datetime.date(2030, 1, 10)],
        "start_time": datetime.time(9, 0),
        "end_time": datetime.time(12, 0),
        "period": 30,
        "total_amount": Decimal("50000.00"),
        "deposit_amount": Decimal("10000.00"),
    }
    data.update(fields)
    data.setdefault("doctor", make_doctor())
    data.setdefault("examination_type", make_examination_type())
    return ExaminationPack.objects.create(**data)


def make_examination(**fields):
    data = {
        "date": datetime.date(2030, 1, 10),
        "time": datetime.time(9, 0),
        "is_lock": False,
        "total_amount": Decimal("50000.00"),
        "deposit_amount": Decimal("10000.00"),
    }
    data.update(fields)
    data.setdefault("doctor", make_doctor())
    data.setdefault("examination_type", make_examination_type())
    return Examination.objects.create(**data)


def make_order(**fields):
    data = {"first_name": "Tuya", "last_name": "Gan", "phone": "99112233", "register": "УБ90010112"}
    data.update(fields)
    data.setdefault("examination", make_examination())
    return Order.objects.create(**data)


def make_invoice(**fields):
    data = {"amount": Decimal("10000.00"), "qpay_invoice_id": "qpay-inv-1"}
    data.update(fields)
    data.setdefault("order", make_order())
    return Invoice.objects.create(**data)


class AdminAPITestCase(APITestCase):
    """API test case whose client is logged in as a superuser (passes DjangoModelPermissions)."""

    def setUp(self):
        super().setUp()
        self.admin = make_user(superuser=True)
        self.client.force_authenticate(self.admin)

    def results(self, response):
        """List payload with or without LimitOffsetPagination."""
        data = response.json()
        return data["results"] if isinstance(data, dict) and "results" in data else data
