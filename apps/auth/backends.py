from django.contrib.auth.backends import ModelBackend
from apps.user.services import UserService


class AuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user, error = UserService.get_by_email(username)

        if not error and not user:
            user, error = UserService.get_by_phone(username)

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
