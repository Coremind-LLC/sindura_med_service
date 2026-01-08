from apps.user.models import User
from apps.common.models import Status
import logging

logger = logging.getLogger(__name__)


class UserService:

    @staticmethod
    def exist_by_phone(phone):
        try:
            response = User.objects.filter(
                phone=phone, is_active=True, status=Status.ACTIVE
            ).exists()
            return response, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def exist_by_email(email):
        try:
            response = User.objects.filter(
                email=email, is_active=True, status=Status.ACTIVE
            ).exists()
            return response, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_by_id(id):
        return User.objects.get(id=id)

    @staticmethod
    def get_by_phone(phone):
        try:
            response = User.objects.get(
                phone=phone, is_active=True, status=Status.ACTIVE
            )
            return response, None
        except User.DoesNotExist:
            return None, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_by_email(email):
        try:
            response = User.objects.get(
                email=email, is_active=True, status=Status.ACTIVE
            )
            return response, None
        except User.DoesNotExist:
            return None, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def update(user):
        try:
            user.save()

            return user, None
        except Exception as e:
            return None, str(e)