"""Tests for the shared helpers package (helpers/ is not an app, so they live here)."""
import datetime

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from apps.activity_log.enums import ActivityLogAction, ActivityLogModel
from apps.activity_log.models import ActivityLog
from helpers.common_helper import CommonHelper
from helpers.number_helper import NumberHelper
from helpers.tests_factories import make_user
from helpers.validator_helper import ValidatorHelper


class ValidatorHelperTests(SimpleTestCase):
    def check_table(self, func, table):
        for value, expected in table:
            with self.subTest(func=func.__name__, value=value):
                self.assertIs(bool(func(value)), expected)

    def test_is_valid_phone(self):
        self.check_table(
            ValidatorHelper.is_valid_phone,
            [("99112233", True), ("9911223", False), ("991122334", False), ("9911a233", False), ("", False)],
        )

    def test_is_valid_email(self):
        self.check_table(
            ValidatorHelper.is_valid_email,
            [("a@example.com", True), ("a.b+c@sub.example.mn", True), ("not-an-email", False), ("a@", False)],
        )

    def test_is_valid_register(self):
        self.check_table(
            ValidatorHelper.is_valid_register,
            [
                ("1234567", True),
                ("123456a", False),
                ("УБ90010112", True),
                ("AB90010112", False),
                ("УБ9001011", False),
                ("12345", False),
            ],
        )

    def test_validate_phone_accepts_valid_number(self):
        self.assertIsNone(ValidatorHelper.validate_phone("88001122"))

    def test_validate_phone_rejects_invalid_numbers(self):
        cases = {"8800112a": "only contain digits", "880011": "exactly 8 digits"}
        for value, message in cases.items():
            with self.subTest(value=value), self.assertRaisesMessage(ValidationError, message):
                ValidatorHelper.validate_phone(value)


class NumberHelperTests(SimpleTestCase):
    def test_random_number_has_requested_digit_count(self):
        for digits in (1, 4, 6):
            with self.subTest(digits=digits):
                values = {NumberHelper.get_random_number(digits) for _ in range(50)}
                self.assertTrue(all(len(str(v)) == digits for v in values))


class CommonHelperTests(TestCase):
    def test_serialize_model_flattens_foreign_keys_and_dates(self):
        user = make_user()
        log = ActivityLog.objects.create(
            action=ActivityLogAction.CREATE,
            model=ActivityLogModel.DOCTOR,
            object_id=5,
            description="created",
            body={"a": 1},
            user=user,
            created_by=user,
        )
        data = CommonHelper.serialize_model(log)
        self.assertEqual(data["user"], user.id)
        self.assertEqual(data["created_by"], user.id)
        self.assertIsNone(data["updated_by"])
        self.assertEqual(data["body"], {"a": 1})
        self.assertEqual(data["created_at"], log.created_at.isoformat())
        self.assertEqual(datetime.datetime.fromisoformat(data["updated_at"]), log.updated_at)
