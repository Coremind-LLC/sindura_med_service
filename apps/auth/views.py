import random
import string
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from apps.auth.serializers import (
    AuthLoginSerializer,
    AuthForgotPasswordSerializer,
    AuthRecoverPasswordSerializer,
    AuthConfirmOTPSerializer,
)
from apps.user.services import UserService
from helpers.number_helper import NumberHelper
from helpers.validator_helper import ValidatorHelper


class AuthViewSet(ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        method="post",
        request_body=AuthLoginSerializer,
        responses={200: openapi.Response("Token")},
    )
    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username:
            return Response(
                {"message": "Нэвтрэх нэр оруулна уу"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not password:
            return Response(
                {"message": "Нууц үг оруулна уу"}, status=status.HTTP_400_BAD_REQUEST
            )

        if (
            not ValidatorHelper.is_valid_phone(username)
            and not ValidatorHelper.is_valid_email(username)
            and not ValidatorHelper.is_valid_register(username)
        ):
            return Response(
                {
                    "message": "Буруу утас, имэйл эсвэл харилцагчийн регистр оруулсан байна"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=username, password=password, is_active=True)
        if user is None:
            return Response(
                {"message": "Нууц үг буруу байна"}, status=status.HTTP_400_BAD_REQUEST
            )

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        token, created = Token.objects.get_or_create(user=user)

        return Response({"token": token.key})

    @swagger_auto_schema(
        method="post",
        request_body=AuthForgotPasswordSerializer,
        responses={200: openapi.Response("OTP sent")},
    )
    @action(detail=False, methods=["post"], url_path="forgot-password")
    def forgot_password(self, request):
        username = request.data.get("username")

        if not username:
            return Response(
                {"message": "Нэвтрэх нэр оруулна уу"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ValidatorHelper.is_valid_phone(
            username
        ) and not ValidatorHelper.is_valid_email(username):
            return Response(
                {"message": "Буруу утас эсвэл имэйл оруулсан байна"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not UserService.get_by_phone(username) and not UserService.get_by_email(
            username
        ):
            return Response(
                {"message": "Утас эсвэл имэйл дээр хэрэглэгч олдсонгүй"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = str(NumberHelper.get_random_number(4))

        cache_key = f"otp:{username}"
        cache.set(cache_key, otp, timeout=300)

        if ValidatorHelper.is_valid_phone(username):
            _, error = CallProService.send(
                to=username, text=f"Tanii batalgaajuulakh code: {otp}."
            )
            if error:
                return Response(
                    {"message": f"Failed to send OTP: {error}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        if ValidatorHelper.is_valid_email(username):
            return Response(
                {"message": "Email connection not ready"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"message": "OTP sent"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        request_body=AuthConfirmOTPSerializer,
        responses={200: openapi.Response("OTP sent")},
    )
    @action(detail=False, methods=["post"], url_path="confirm-otp")
    def confirm_otp(self, request):
        username = request.data.get("username")
        otp = request.data.get("otp")

        if not username:
            return Response(
                {"message": "Username is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not otp:
            return Response(
                {"message": "OTP is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not ValidatorHelper.is_valid_phone(
            username
        ) and not ValidatorHelper.is_valid_email(username):
            return Response(
                {"message": "Invalid phone or email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not UserService.get_by_phone(username) and not UserService.get_by_email(
            username
        ):
            return Response(
                {"message": "Phone or email not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"otp:{username}"
        cached_otp = cache.get(cache_key)

        if not cached_otp:
            return Response(
                {"message": "OTP has expired or is invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cached_otp != otp:
            return Response(
                {"message": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )

        secret = "".join(random.choices(string.ascii_letters + string.digits, k=10))

        cache_key = f"secret:{username}"
        cache.set(cache_key, secret, timeout=300)

        return Response({"secret": secret}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        request_body=AuthRecoverPasswordSerializer,
        responses={200: openapi.Response("Password reset successfully")},
    )
    @action(detail=False, methods=["post"], url_path="recover-password")
    def recover_password(self, request):
        username = request.data.get("username")
        secret = request.data.get("secret")
        new_password = request.data.get("new_password")

        if not username:
            return Response(
                {"message": "Username is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not secret:
            return Response(
                {"message": "Secret is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_password:
            return Response(
                {"message": "New password is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ValidatorHelper.is_valid_phone(
            username
        ) and not ValidatorHelper.is_valid_email(username):
            return Response(
                {"message": "Invalid phone or email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"secret:{username}"
        cached_secret = cache.get(cache_key)

        if not cached_secret:
            return Response(
                {"message": "Secret has expired or is invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cached_secret != secret:
            return Response(
                {"message": "Invalid secret."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not UserService.exist_by_phone(username) and not UserService.exist_by_email(
            username
        ):
            return Response(
                {"message": "Phone or email not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, error = UserService.get_by_phone(username)
        if error:
            return Response(
                {"message": f"Failed to find user: {error}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if user is None:
            return Response(
                {"message": "User not found."}, status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)

        _, error = UserService.update(user)
        if error:
            return Response(
                {"message": f"Failed to update user: {error}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        cache.delete(cache_key)

        return Response(
            {"message": "Password reset successfully."}, status=status.HTTP_200_OK
        )