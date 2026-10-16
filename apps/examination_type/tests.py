from django.test import override_settings

from apps.common.enums import Status
from apps.doctor.tests import SoftDeleteResourceMixin
from apps.examination_type.models import ExaminationType
from apps.examination_type.services import ExaminationTypeService
from helpers.tests_factories import AdminAPITestCase, make_examination_type


class ExaminationTypeAPITests(SoftDeleteResourceMixin, AdminAPITestCase):
    url = "/examination-types/"
    model = ExaminationType
    fk_name = "examination_type"
    search_field = "name"
    label = "examination type"

    def make_resource(self, **fields):
        return make_examination_type(**fields)

    def valid_payload(self):
        return {"name": "Endoscopy", "icon": "stomach.svg"}

    def test_icon_is_optional_and_returned_as_null(self):
        response = self.client.post(self.url, {"name": "X-ray", "icon": None}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()["icon"])
        self.assertFalse(response.json()["archived"])

    def test_name_too_short_is_rejected(self):
        response = self.client.post(self.url, {"name": "X"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json())

    def test_default_list_hides_archived(self):
        visible = make_examination_type()
        make_examination_type(archived=True)
        self.assertEqual(self.listed_ids(), [visible.pk])

    def test_archived_query_param_selects_by_flag_among_active_rows(self):
        active = make_examination_type()
        archived = make_examination_type(archived=True)
        for status in (Status.DELETED, Status.INACTIVE):
            make_examination_type(status=status)
            make_examination_type(status=status, archived=True)
        cases = [("true", [archived.pk]), ("TRUE", [archived.pk]), ("false", [active.pk])]
        for value, expected in cases:
            with self.subTest(archived=value):
                self.assertEqual(self.listed_ids({"archived": value}), expected)

    def test_retrieve_ignores_list_filters(self):
        archived = make_examination_type(archived=True)
        response = self.client.get(self.detail_url(archived))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["archived"])
        response = self.client.get(self.detail_url(archived), {"archived": "false"})
        self.assertEqual(response.status_code, 404)

    def test_archive_and_unarchive_actions(self):
        exam_type = make_examination_type()
        for action, flag in (("archive", True), ("unarchive", False)):
            with self.subTest(action=action):
                response = self.client.post(f"{self.detail_url(exam_type)}{action}/")
                self.assertEqual(response.status_code, 200)
                self.assertIs(response.json()["archived"], flag)
                exam_type.refresh_from_db()
                self.assertIs(exam_type.archived, flag)

    def test_archive_requires_authentication(self):
        exam_type = make_examination_type()
        self.client.force_authenticate(None)
        response = self.client.post(f"{self.detail_url(exam_type)}archive/")
        self.assertIn(response.status_code, (401, 403))
        exam_type.refresh_from_db()
        self.assertFalse(exam_type.archived)


class ExaminationTypeServiceTests(AdminAPITestCase):
    def test_delete_marks_type_deleted(self):
        exam_type = make_examination_type()
        returned = ExaminationTypeService.delete(exam_type.pk, self.admin)
        exam_type.refresh_from_db()
        self.assertEqual(returned.pk, exam_type.pk)
        self.assertEqual(exam_type.status, Status.DELETED)
        self.assertEqual(exam_type.updated_by, self.admin)


@override_settings(CORS_ALLOW_ALL_ORIGINS=False)
class CorsTests(AdminAPITestCase):
    """Production CORS: only the admin panel and the patient site may call the API from a browser."""

    def origin_header(self, origin):
        response = self.client.get("/examination-types/", HTTP_ORIGIN=origin)
        return response.headers.get("Access-Control-Allow-Origin")

    def test_only_known_frontends_are_allowed(self):
        for origin in ("https://sindura-med-admin.monos.mn", "https://sindura-med.monos.mn"):
            with self.subTest(origin=origin):
                self.assertEqual(self.origin_header(origin), origin)
        self.assertIsNone(self.origin_header("https://evil.example.com"))
