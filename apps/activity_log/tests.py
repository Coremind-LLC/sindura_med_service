from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase

from apps.activity_log.enums import ActivityLogAction, ActivityLogModel
from apps.activity_log.models import ActivityLog
from apps.activity_log.services import ActivityLogService
from helpers.tests_factories import AdminAPITestCase, make_user


class ActivityLogServiceTests(TestCase):
    def test_create_copies_user_names(self):
        user = make_user(first_name="Oyun", last_name="Erdene")
        log = ActivityLogService.create(
            ActivityLogAction.APPROVE, ActivityLogModel.ORDER, object_id=7, description="ok", body={"k": "v"}, user=user
        )
        log.refresh_from_db()
        self.assertEqual((log.action, log.object_id, log.body), ("APPROVE", 7, {"k": "v"}))
        self.assertEqual((log.user, log.user_first_name, log.user_last_name), (user, "Oyun", "Erdene"))

    def test_create_ignores_non_user_values(self):
        for value in (None, "anonymous", 42):
            with self.subTest(user=value):
                log = ActivityLogService.create(ActivityLogAction.DELETE, ActivityLogModel.DOCTOR, user=value)
                self.assertIsNone(log.user)
                self.assertEqual(log.user_first_name, "")
                self.assertEqual(log.description, "")


class OrderModelValueMigrationTests(TestCase):
    before = [("activity_log", "0006_alter_activitylog_action_and_more")]
    after = [("activity_log", "0007_order_model_value")]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)

    def test_enum_value_has_no_trailing_space(self):
        self.assertEqual(ActivityLogModel.ORDER, "ORDER")
        log = ActivityLogService.create(ActivityLogAction.CREATE, ActivityLogModel.ORDER, object_id=1)
        log.refresh_from_db()
        self.assertEqual(log.model, "ORDER")

    def test_migration_rewrites_old_rows_and_reverses(self):
        self.addCleanup(self.migrate, self.after)
        self.migrate(self.before)
        old = ActivityLog.objects.create(action="CREATE", model="ORDER ", object_id=1)
        doctor = ActivityLog.objects.create(action="CREATE", model="DOCTOR", object_id=2)
        self.migrate(self.after)
        old.refresh_from_db()
        self.assertEqual(old.model, "ORDER")
        self.migrate(self.before)
        old.refresh_from_db()
        doctor.refresh_from_db()
        self.assertEqual((old.model, doctor.model), ("ORDER ", "DOCTOR"))


class ActivityLogAPITests(AdminAPITestCase):
    def payload(self, **overrides):
        data = {"action": "CREATE", "model": "DOCTOR", "objectId": 3, "description": "Doctor created"}
        data.update(overrides)
        return data

    def test_create_sets_created_by(self):
        response = self.client.post("/activity-logs/", self.payload(body={"name": "x"}), format="json")
        self.assertEqual(response.status_code, 201)
        log = ActivityLog.objects.get(pk=response.json()["id"])
        self.assertEqual(log.created_by, self.admin)
        self.assertEqual((log.model, log.object_id, log.body), ("DOCTOR", 3, {"name": "x"}))

    def test_create_requires_core_fields(self):
        for field in ("action", "model", "objectId", "description"):
            with self.subTest(field=field):
                data = self.payload()
                data.pop(field)
                response = self.client.post("/activity-logs/", data, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertFalse(ActivityLog.objects.exists())

    def test_list_filters_and_hides_deleted(self):
        ActivityLog.objects.bulk_create(
            [
                ActivityLog(action="CREATE", model="DOCTOR", object_id=1, description="first"),
                ActivityLog(action="UPDATE", model="EXAMINATION", object_id=2, description="second"),
                ActivityLog(action="DELETE", model="DOCTOR", object_id=3, description="gone", status="DELETED"),
            ]
        )
        rows = self.results(self.client.get("/activity-logs/"))
        self.assertEqual([row["description"] for row in rows], ["second", "first"])
        rows = self.results(self.client.get("/activity-logs/", {"model": "EXAMINATION"}))
        self.assertEqual([row["objectId"] for row in rows], [2])

    def test_non_admin_without_permission_cannot_create(self):
        self.client.force_authenticate(make_user())
        self.assertEqual(self.client.get("/activity-logs/").status_code, 200)
        self.assertEqual(self.client.post("/activity-logs/", self.payload(), format="json").status_code, 403)

    def test_retrieve_and_partial_update_record_editor(self):
        log = ActivityLogService.create(ActivityLogAction.CREATE, ActivityLogModel.EXAMINATION, object_id=9, description="d")
        url = f"/activity-logs/{log.id}/"
        self.assertEqual(self.client.get(url).json()["model"], "EXAMINATION")
        response = self.client.patch(url, {"description": "edited"}, format="json")
        self.assertEqual(response.status_code, 200)
        log.refresh_from_db()
        self.assertEqual((log.description, log.updated_by), ("edited", self.admin))
