from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from apps.common.enums import Status
from apps.user.models import User
from apps.user.services import UserService


# Fields nobody can write through the API: account status is managed by delete/activate,
# and groups/permissions are managed in the Django admin.
PROTECTED_FIELDS = ("status", "groups", "user_permissions", "last_login", "date_joined")
PROFILE_FIELDS = frozenset({"email", "phone", "first_name", "last_name"})
ADMIN_FIELDS = PROFILE_FIELDS | {"is_active", "is_staff"}


class UserSerializer(serializers.ModelSerializer):
    """User management serializer (requires the user model permissions)."""

    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = PROTECTED_FIELDS
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def writable_fields(self) -> frozenset[str]:
        """Model fields the requesting user may set; only superusers grant superuser."""
        request = self.context.get("request")
        if request is not None and request.user.is_superuser:
            return ADMIN_FIELDS | {"is_superuser"}
        return ADMIN_FIELDS

    def create(self, validated_data) -> User:
        exist_phone, error = UserService.exist_by_phone(validated_data["phone"])
        if error:
            raise serializers.ValidationError({"error": str(error)})
        if exist_phone:
            raise serializers.ValidationError({"phone": "Утас дээр бүртгэлтэй тул үүсгэх боломжгүй"})
        exist_email, error = UserService.exist_by_email(validated_data["email"])
        if error:
            raise serializers.ValidationError({"error": str(error)})
        if exist_email:
            raise serializers.ValidationError({"email": "Имейл дээр бүртгэлтэй тул үүсгэх боломжгүй"})

        allowed = self.writable_fields() | {"password"}
        data = {key: value for key, value in validated_data.items() if key in allowed}
        return User.objects.create_user(**data)

    def update(self, instance, validated_data) -> User:
        # Passwords only change through the change-password / recover-password flows.
        for field in self.writable_fields():
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()

        return instance

    def delete(self) -> None:
        self.instance.is_active = False
        self.instance.status = Status.DELETED
        self.instance.save()


class UserSelfSerializer(UserSerializer):
    """A user editing their own profile: only personal details, never access flags."""

    class Meta(UserSerializer.Meta):
        read_only_fields = PROTECTED_FIELDS + ("is_active", "is_staff", "is_superuser")

    def writable_fields(self) -> frozenset[str]:
        return PROFILE_FIELDS


class UserChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs) -> dict:
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"message": "Passwords do not match"})
        return attrs