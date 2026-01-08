from rest_framework import serializers


class AuthLoginSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Phone or email")
    password = serializers.CharField(help_text="Password", write_only=True)


class AuthForgotPasswordSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Phone or email")


class AuthConfirmOTPSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Phone or email")
    otp = serializers.CharField(help_text="OTP")


class AuthRecoverPasswordSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Phone or email")
    secret = serializers.CharField(help_text="Secret")
    new_password = serializers.CharField(help_text="New password", write_only=True)
