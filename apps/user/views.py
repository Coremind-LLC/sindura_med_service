from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.user.models import User
from apps.user.permissions import UserModelPermissions
from apps.user.serializers import (
    UserChangePasswordSerializer,
    UserSelfSerializer,
    UserSerializer,
)

# Actions that only touch request.user: open to any authenticated user.
SELF_SERVICE_ACTIONS = frozenset({"update_self", "change_password", "get_profile"})


class UserViewSet(BaseViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [UserModelPermissions]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in SELF_SERVICE_ACTIONS:
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=["put"], url_path="self")
    def update_self(self, request) -> Response:
        user = request.user
        serializer = UserSelfSerializer(
            user, data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request) -> Response:
        user = request.user
        serializer = UserChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not check_password(old_password, user.password):
            return Response(
                {"message": "Old password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Your password has been updated successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"], url_path="activate")
    def activate(self, request, pk=None) -> Response:
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user.is_active = True
        user.save()
        return Response({"message": "User activated"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="deactivate")
    def deactivate(self, request, pk=None) -> Response:
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user.is_active = False
        user.save()
        return Response({"message": "User deactivated"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="profile")
    def get_profile(self, request) -> Response:
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)