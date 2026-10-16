from apps.common.enums import Status
from apps.doctor.models import Doctor
from apps.doctor.services import DoctorService
from helpers.tests_factories import (
    AdminAPITestCase,
    make_doctor,
    make_examination,
    make_examination_pack,
)


class SoftDeleteResourceMixin:
    """CRUD, soft-delete and BaseFilter checks for resources served by BaseViewSet.

    Concrete classes set ``url``, ``model``, ``fk_name`` (the FK name used by packs and
    examinations), ``search_field`` and implement ``make_resource`` / ``valid_payload``.
    """

    url = ""
    model = None
    fk_name = ""
    search_field = ""
    label = ""

    def make_resource(self, **fields):
        raise NotImplementedError

    def valid_payload(self):
        raise NotImplementedError

    def detail_url(self, obj):
        return f"{self.url}{obj.pk}/"

    def listed_ids(self, query=None):
        response = self.client.get(self.url, query or {})
        self.assertEqual(response.status_code, 200)
        return [row["id"] for row in self.results(response)]

    def test_create_persists_resource(self):
        payload = self.valid_payload()
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual({k: body[k] for k in payload}, payload)
        self.assertEqual(self.model.objects.get(pk=body["id"]).status, Status.ACTIVE)

    def test_create_ignores_client_supplied_status(self):
        payload = {**self.valid_payload(), "status": Status.DELETED}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.model.objects.get(pk=response.json()["id"]).status, Status.ACTIVE)

    def test_list_returns_only_active_rows_newest_first(self):
        older, newer = self.make_resource(), self.make_resource()
        self.make_resource(status=Status.DELETED)
        self.make_resource(status=Status.INACTIVE)
        self.assertEqual(self.listed_ids(), [newer.pk, older.pk])

    def test_list_filters_by_icontains_and_sorts(self):
        alpha = self.make_resource(**{self.search_field: "Alpha"})
        beta = self.make_resource(**{self.search_field: "Albeta"})
        self.make_resource(**{self.search_field: "Gamma"})
        param = self.search_field  # query params are not camelCase-parsed
        cases = [
            ({self.search_field: "AL", "sort": param}, [beta.pk, alpha.pk]),
            ({self.search_field: "al", "sort": f"-{param}"}, [alpha.pk, beta.pk]),
            ({self.search_field: "pha", "unknownField": "x"}, [alpha.pk]),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(self.listed_ids(query), expected)

    def test_anonymous_can_read_but_not_write(self):
        obj = self.make_resource()
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url(obj)).status_code, 200)
        response = self.client.post(self.url, self.valid_payload(), format="json")
        self.assertIn(response.status_code, (401, 403))
        self.assertIn(self.client.delete(self.detail_url(obj)).status_code, (401, 403))
        self.assertEqual(self.model.objects.count(), 1)

    def test_partial_update_changes_field(self):
        obj = self.make_resource()
        response = self.client.patch(
            self.detail_url(obj), {self.search_field: "Renamed"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        obj.refresh_from_db()
        self.assertEqual(getattr(obj, self.search_field), "Renamed")

    def test_retrieve_unknown_id_returns_404(self):
        self.assertEqual(self.client.get(f"{self.url}999999/").status_code, 404)

    def test_destroy_soft_deletes_and_records_user(self):
        obj = self.make_resource()
        response = self.client.delete(self.detail_url(obj))
        self.assertEqual(response.status_code, 204)
        obj.refresh_from_db()
        self.assertEqual(obj.status, Status.DELETED)
        self.assertEqual(obj.updated_by, self.admin)
        self.assertNotIn(obj.pk, self.listed_ids())

    def test_destroy_blocked_while_linked_rows_are_active(self):
        builders = {
            "examination packs": make_examination_pack,
            "examinations": make_examination,
        }
        for kind, builder in builders.items():
            with self.subTest(kind=kind):
                obj = self.make_resource()
                builder(**{self.fk_name: obj})
                response = self.client.delete(self.detail_url(obj))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["message"],
                    f"Cannot delete {self.label} because they have active {kind}.",
                )
                obj.refresh_from_db()
                self.assertEqual(obj.status, Status.ACTIVE)

    def test_destroy_allowed_when_linked_rows_are_deleted(self):
        obj = self.make_resource()
        make_examination_pack(status=Status.DELETED, **{self.fk_name: obj})
        make_examination(status=Status.DELETED, **{self.fk_name: obj})
        self.assertEqual(self.client.delete(self.detail_url(obj)).status_code, 204)
        obj.refresh_from_db()
        self.assertEqual(obj.status, Status.DELETED)


class DoctorAPITests(SoftDeleteResourceMixin, AdminAPITestCase):
    url = "/doctors/"
    model = Doctor
    fk_name = "doctor"
    search_field = "first_name"
    label = "doctor"

    def make_resource(self, **fields):
        return make_doctor(**fields)

    def valid_payload(self):
        return {
            "firstName": "Oyun",
            "lastName": "Erdene",
            "position": "Cardiologist",
            "email": "oyun@example.com",
            "image": "/media/images/oyun.png",
        }

    def test_optional_fields_round_trip_as_null(self):
        payload = {"firstName": "Oyun", "lastName": "Erdene", "position": "Nurse", "image": None}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()["image"])
        self.assertIsNone(response.json()["email"])

    def test_field_validation_errors(self):
        cases = {
            "firstName": {"firstName": "A"},
            "position": {"position": ""},
            "email": {"email": "not-an-email"},
        }
        for field, override in cases.items():
            with self.subTest(field=field):
                payload = {**self.valid_payload(), **override}
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())

    def test_email_must_be_unique_among_active_doctors_case_insensitively(self):
        make_doctor(email="Oyun@Example.com")
        response = self.client.post(self.url, self.valid_payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["email"], ["Email already exists"])

    def test_email_of_deleted_doctor_can_be_reused(self):
        make_doctor(email="oyun@example.com", status=Status.DELETED)
        response = self.client.post(self.url, self.valid_payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)

    def test_missing_email_never_counts_as_duplicate(self):
        make_doctor(email="")
        base = {"firstName": "Oyun", "lastName": "Erdene", "position": "Nurse"}
        created = []
        for email in (None, ""):
            with self.subTest(email=email):
                response = self.client.post(self.url, {**base, "email": email}, format="json")
                self.assertEqual(response.status_code, 201, response.content)
                self.assertIsNone(response.json()["email"])
                created.append(response.json()["id"])
        stored = Doctor.objects.filter(pk__in=created).values_list("email", flat=True)
        self.assertEqual(list(stored), ["", ""])

    def test_update_may_clear_email_when_others_have_none(self):
        make_doctor(email="")
        doctor = make_doctor(email="clear@example.com")
        response = self.client.patch(self.detail_url(doctor), {"email": None}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        doctor.refresh_from_db()
        self.assertEqual(doctor.email, "")

    def test_update_may_keep_own_email(self):
        doctor = make_doctor(email="keep@example.com")
        response = self.client.patch(
            self.detail_url(doctor), {"email": "KEEP@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        doctor.refresh_from_db()
        self.assertEqual(doctor.email, "KEEP@example.com")


class DoctorServiceTests(AdminAPITestCase):
    def test_exists_by_email(self):
        doctor = make_doctor(email="dup@example.com")
        self.assertTrue(DoctorService.exists_by_email("DUP@example.com"))
        self.assertFalse(DoctorService.exists_by_email("dup@example.com", exclude_id=doctor.pk))
        self.assertFalse(DoctorService.exists_by_email("other@example.com"))

    def test_exists_by_email_ignores_empty_email(self):
        make_doctor(email="")
        self.assertFalse(DoctorService.exists_by_email(""))
        self.assertFalse(DoctorService.exists_by_email(None))

    def test_delete_marks_doctor_deleted(self):
        doctor = make_doctor()
        returned = DoctorService.delete(doctor.pk, self.admin)
        doctor.refresh_from_db()
        self.assertEqual(returned.pk, doctor.pk)
        self.assertEqual(doctor.status, Status.DELETED)
        self.assertEqual(doctor.updated_by, self.admin)
        self.assertIsNotNone(doctor.updated_at)
