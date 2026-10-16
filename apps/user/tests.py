from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.common.enums import Status
from apps.user.models import User
from apps.user.serializers import UserChangePasswordSerializer, UserSerializer
from apps.user.services import UserService
from helpers.tests_factories import TEST_PASSWORD, AdminAPITestCase, make_user

STRONG_PASSWORD = "Zx8!qLm#40vT"


class UserManagerTests(TestCase):
    def test_create_user_normalizes_email_and_hashes_password(self):
        user = make_user(email="Someone@EXAMPLE.COM")
        self.assertEqual(user.email, "Someone@example.com")
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(user.status, Status.ACTIVE)

    def test_create_superuser_sets_flags(self):
        admin = make_user(superuser=True)
        self.assertTrue(admin.is_staff and admin.is_superuser)

    def test_required_fields_and_superuser_flags_are_enforced(self):
        cases = [
            (User.objects.create_user, {"email": "", "phone": "88112233"}, "Email is required"),
            (User.objects.create_user, {"email": "x@example.com", "phone": ""}, "Phone is required"),
            (User.objects.create_superuser, {"email": "y@example.com", "phone": "88112234", "is_staff": False}, "is_staff"),
            (User.objects.create_superuser, {"email": "z@example.com", "phone": "88112235", "is_superuser": False}, "is_superuser"),
        ]
        for create, fields, message in cases:
            with self.subTest(fields=fields), self.assertRaisesMessage(ValueError, message):
                create(first_name="A", last_name="B", **fields)


class UserServiceTests(TestCase):
    def setUp(self):
        self.user = make_user(email="svc@example.com", phone="88776655")
        self.deleted = make_user(email="gone@example.com", phone="88776644", status=Status.DELETED)

    def test_lookups_find_only_active_users(self):
        self.assertEqual(UserService.get_by_phone("88776655"), (self.user, None))
        self.assertEqual(UserService.get_by_email("svc@example.com"), (self.user, None))
        self.assertEqual(UserService.get_by_phone("88776644"), (None, None))
        self.assertEqual(UserService.get_by_email("gone@example.com"), (None, None))
        self.assertEqual(UserService.get_by_id(self.user.id), self.user)

    def test_get_by_username_dispatches_on_phone_or_email(self):
        self.assertEqual(UserService.get_by_username("88776655"), (self.user, None))
        self.assertEqual(UserService.get_by_username("svc@example.com"), (self.user, None))
        self.assertEqual(UserService.get_by_username("99999999"), (None, None))
        self.assertEqual(UserService.get_by_username("gone@example.com"), (None, None))

    def test_exists_checks(self):
        self.assertEqual(UserService.exist_by_phone("88776655"), (True, None))
        self.assertEqual(UserService.exist_by_email("gone@example.com"), (False, None))

    def test_update_persists_changes(self):
        self.user.first_name = "Changed"
        user, error = UserService.update(self.user)
        self.assertIsNone(error)
        self.assertEqual(User.objects.get(pk=user.pk).first_name, "Changed")


class UserSerializerTests(TestCase):
    def test_delete_deactivates_and_marks_deleted(self):
        user = make_user()
        UserSerializer(user).delete()
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.status, Status.DELETED)

    def test_change_password_serializer_requires_matching_confirmation(self):
        data = {"old_password": "a", "new_password": STRONG_PASSWORD, "confirm_password": "nope"}
        serializer = UserChangePasswordSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["message"], ["Passwords do not match"])


class UserAnonymousTests(APITestCase):
    def test_endpoints_require_authentication(self):
        self.assertEqual(self.client.get("/users/").status_code, 401)
        self.assertEqual(self.client.get("/users/profile/").status_code, 401)


class UserAPITests(AdminAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="api@example.com", phone="88990011")

    def user_payload(self, **overrides):
        data = {"email": "new@example.com", "phone": "88445566", "firstName": "Saraa", "lastName": "Tseren"}
        data.update(overrides)
        return data

    def test_create_user_hashes_password_and_hides_it(self):
        response = self.client.post("/users/", self.user_payload(password=STRONG_PASSWORD), format="json")
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertNotIn("password", body)
        self.assertEqual(body["firstName"], "Saraa")
        self.assertTrue(User.objects.get(email="new@example.com").check_password(STRONG_PASSWORD))

    def test_create_user_rejects_duplicate_active_phone(self):
        response = self.client.post("/users/", self.user_payload(phone="88990011"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", str(response.json()))
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_create_user_rejects_duplicate_active_email(self):
        response = self.client.post("/users/", self.user_payload(email="api@example.com"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        # The serializer's own duplicate check reports under "email", not "phone".
        with self.assertRaises(ValidationError) as ctx:
            UserSerializer().create({"email": "api@example.com", "phone": "88445566"})
        self.assertEqual(ctx.exception.detail, {"email": "Имейл дээр бүртгэлтэй тул үүсгэх боломжгүй"})

    def test_superuser_can_grant_admin_flags_but_not_groups_or_status(self):
        group = Group.objects.create(name="ops")
        payload = {"isSuperuser": True, "isStaff": True, "status": "deleted", "groups": [group.id]}
        response = self.client.patch(f"/users/{self.user.id}/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_superuser and self.user.is_staff)
        self.assertEqual(self.user.status, Status.ACTIVE)
        self.assertFalse(self.user.groups.exists())

    def test_create_user_rejects_invalid_phone(self):
        response = self.client.post("/users/", self.user_payload(phone="12ab"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.json())

    def test_profile_returns_current_user(self):
        response = self.client.get("/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.admin.email)
        self.assertNotIn("password", response.json())

    def test_update_self_changes_allowed_fields_but_not_password(self):
        payload = self.user_payload(email=self.admin.email, phone=self.admin.phone, password="ignored-pass-1")
        response = self.client.put("/users/self/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.first_name, self.admin.last_name), ("Saraa", "Tseren"))
        self.assertTrue(self.admin.check_password(TEST_PASSWORD))

    def test_patch_updates_other_user(self):
        response = self.client.patch(f"/users/{self.user.id}/", {"lastName": "Updated"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, "Updated")

    def test_change_password(self):
        url = "/users/change-password/"
        mismatch = {"oldPassword": TEST_PASSWORD, "newPassword": STRONG_PASSWORD, "confirmPassword": "different"}
        self.assertEqual(self.client.post(url, mismatch, format="json").status_code, 400)
        wrong_old = dict(mismatch, oldPassword="wrong", confirmPassword=STRONG_PASSWORD)
        response = self.client.post(url, wrong_old, format="json")
        self.assertEqual(response.json(), {"message": "Old password is incorrect"})
        weak = dict(wrong_old, oldPassword=TEST_PASSWORD, newPassword="123", confirmPassword="123")
        self.assertEqual(self.client.post(url, weak, format="json").status_code, 400)
        ok = dict(wrong_old, oldPassword=TEST_PASSWORD)
        response = self.client.post(url, ok, format="json")
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(STRONG_PASSWORD))

    def test_activate_and_deactivate(self):
        for name, expected in (("deactivate", False), ("activate", True)):
            with self.subTest(action=name):
                response = self.client.patch(f"/users/{self.user.id}/{name}/")
                self.assertEqual(response.status_code, 200)
                self.user.refresh_from_db()
                self.assertIs(self.user.is_active, expected)
        missing = self.client.patch("/users/999999/activate/")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"message": "User not found"})

    def test_delete_is_soft_and_hides_user_from_list(self):
        response = self.client.delete(f"/users/{self.user.id}/")
        self.assertEqual(response.status_code, 204)
        self.user.refresh_from_db()
        self.assertEqual(self.user.status, Status.DELETED)
        ids = [row["id"] for row in self.results(self.client.get("/users/"))]
        self.assertIn(self.admin.id, ids)
        self.assertNotIn(self.user.id, ids)

    def test_list_filters_by_field(self):
        response = self.client.get("/users/", {"email": "api@"})
        self.assertEqual([row["id"] for row in self.results(response)], [self.user.id])


class UserPermissionTests(APITestCase):
    """A regular logged-in user: self-service only, no user management."""

    def setUp(self):
        super().setUp()
        self.user = make_user(email="plain@example.com", phone="88123456")
        self.other = make_user(email="other@example.com", phone="88123457")
        self.client.force_authenticate(self.user)

    def grant(self, *codenames):
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
        self.user = User.objects.get(pk=self.user.pk)  # drop the cached permissions
        self.client.force_authenticate(self.user)

    def test_management_endpoints_are_forbidden_without_permissions(self):
        detail = f"/users/{self.other.id}/"
        calls = [
            ("get", "/users/", None),
            ("get", detail, None),
            ("post", "/users/", {"email": "x@example.com", "phone": "88123458"}),
            ("patch", detail, {"lastName": "Hacked"}),
            ("put", detail, {"email": "other@example.com", "phone": "88123457"}),
            ("delete", detail, None),
            ("patch", f"{detail}activate/", None),
            ("patch", f"{detail}deactivate/", None),
        ]
        for method, url, data in calls:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data, format="json")
                self.assertEqual(response.status_code, 403)
        self.other.refresh_from_db()
        self.assertEqual((self.other.last_name, self.other.status, self.other.is_active), ("Dorj", Status.ACTIVE, True))
        self.assertFalse(User.objects.filter(email="x@example.com").exists())

    def test_model_permissions_unlock_management(self):
        self.grant("view_user", "change_user")
        self.assertEqual(self.client.get("/users/").status_code, 200)
        response = self.client.patch(f"/users/{self.other.id}/deactivate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.delete(f"/users/{self.other.id}/").status_code, 403)

    def test_non_superuser_admin_cannot_grant_superuser(self):
        self.grant("change_user")
        response = self.client.patch(f"/users/{self.other.id}/", {"isSuperuser": True, "isStaff": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.other.refresh_from_db()
        self.assertTrue(self.other.is_staff)
        self.assertFalse(self.other.is_superuser)

    def test_self_service_endpoints_stay_available(self):
        self.assertEqual(self.client.get("/users/profile/").json()["email"], "plain@example.com")
        payload = {"oldPassword": TEST_PASSWORD, "newPassword": STRONG_PASSWORD, "confirmPassword": STRONG_PASSWORD}
        self.assertEqual(self.client.post("/users/change-password/", payload, format="json").status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))

    def test_update_self_cannot_escalate_privileges(self):
        group = Group.objects.create(name="admins")
        payload = {
            "email": "plain@example.com",
            "phone": "88123456",
            "firstName": "New",
            "isSuperuser": True,
            "isStaff": True,
            "isActive": False,
            "status": "deleted",
            "groups": [group.id],
            "userPermissions": list(Permission.objects.values_list("id", flat=True)[:3]),
            "password": "taken-over-pass-9",
        }
        response = self.client.put("/users/self/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["isSuperuser"])
        self.user = User.objects.get(pk=self.user.pk)
        self.assertEqual(self.user.first_name, "New")
        flags = (self.user.is_superuser, self.user.is_staff, self.user.is_active, self.user.status)
        self.assertEqual(flags, (False, False, True, Status.ACTIVE))
        self.assertFalse(self.user.groups.exists() or self.user.user_permissions.exists())
        self.assertTrue(self.user.check_password(TEST_PASSWORD))
