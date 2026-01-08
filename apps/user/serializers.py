from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from apps.common.enums import Status
from apps.user.models import User
from apps.user.services import UserService


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def create(self, validated_data):
        exist_phone, error = UserService.exist_by_phone(validated_data["phone"])
        if error:
            raise serializers.ValidationError({"error": str(error)})
        if exist_phone:
            raise serializers.ValidationError(
                {"phone": "Утас дээр бүртгэлтэй тул үүсгэх боломжгүй"}
            )
        exist_email, error = UserService.exist_by_email(validated_data["email"])
        if error:
            raise serializers.ValidationError({"error": str(error)})
        if exist_email:
            raise serializers.ValidationError(
                {"phone": "Имейл дээр бүртгэлтэй тул үүсгэх боломжгүй"}
            )

        user = User.objects.create_user(**validated_data)

        return user

    def update(self, instance, validated_data):
        validated_data.pop("password", None)

        allowed_fields = {
            "email",
            "phone",
            "first_name",
            "last_name",
            "is_active",
            "is_superuser",
            "is_staff",
            "is_primary",
        }

        for field in allowed_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()

        return instance

    def delete(self):
        self.instance.is_active = False
        self.instance.status = Status.DELETED
        self.instance.save()


class UserChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"message": "Passwords do not match"})
        return attrs