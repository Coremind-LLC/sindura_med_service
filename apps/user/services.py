from apps.user.models import User
from apps.common.models import Status
from helpers.validator_helper import ValidatorHelper
import logging

logger = logging.getLogger(__name__)


class UserService:

    @staticmethod
    def exist_by_phone(phone) -> tuple[bool | None, str | None]:
        try:
            response = User.objects.filter(
                phone=phone, is_active=True, status=Status.ACTIVE
            ).exists()
            return response, None
        except Exception as e:
            logger.exception("Failed to check user by phone")
            return None, str(e)

    @staticmethod
    def exist_by_email(email) -> tuple[bool | None, str | None]:
        try:
            response = User.objects.filter(
                email=email, is_active=True, status=Status.ACTIVE
            ).exists()
            return response, None
        except Exception as e:
            logger.exception("Failed to check user by email")
            return None, str(e)

    @staticmethod
    def get_by_id(id) -> User:
        return User.objects.get(id=id)

    @staticmethod
    def get_by_phone(phone) -> tuple[User | None, str | None]:
        try:
            response = User.objects.get(
                phone=phone, is_active=True, status=Status.ACTIVE
            )
            return response, None
        except User.DoesNotExist:
            return None, None
        except Exception as e:
            logger.exception("Failed to get user by phone")
            return None, str(e)

    @staticmethod
    def get_by_email(email) -> tuple[User | None, str | None]:
        try:
            response = User.objects.get(
                email=email, is_active=True, status=Status.ACTIVE
            )
            return response, None
        except User.DoesNotExist:
            return None, None
        except Exception as e:
            logger.exception("Failed to get user by email")
            return None, str(e)

    @staticmethod
    def get_by_username(username) -> tuple[User | None, str | None]:
        """Look a user up by phone when the username is a phone number, otherwise by email."""
        if ValidatorHelper.is_valid_phone(username):
            return UserService.get_by_phone(username)
        return UserService.get_by_email(username)

    @staticmethod
    def update(user) -> tuple[User | None, str | None]:
        try:
            user.save()

            return user, None
        except Exception as e:
            logger.exception("Failed to update user")
            return None, str(e)