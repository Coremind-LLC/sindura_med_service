import datetime
from types import SimpleNamespace

from django.http import Http404

from apps.common.enums import Status
from apps.examination.models import Examination
from apps.examination.services import ExaminationService
from apps.order.enums import OrderStage
from helpers.tests_factories import (
    AdminAPITestCase,
    make_doctor,
    make_examination,
    make_examination_pack,
    make_examination_type,
    make_order,
)

DAY = datetime.date(2030, 1, 10)


class ExaminationAPITests(AdminAPITestCase):
    url = "/examinations/"

    def setUp(self):
        super().setUp()
        self.doctor = make_doctor(first_name="Gerel", image="/media/images/g.png")
        self.exam_type = make_examination_type(name="MRI")

    def payload(self, **overrides):
        data = {
            "date": "2030-01-10",
            "time": "09:00",
            "doctor": self.doctor.pk,
            "examinationType": self.exam_type.pk,
            "totalAmount": "40000.00",
            "depositAmount": "5000.00",
            "room": "204",
        }
        data.update(overrides)
        return data

    def test_create_returns_denormalised_fields_and_sets_creator(self):
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["doctorFirstName"], "Gerel")
        self.assertEqual(body["doctorImage"], "/media/images/g.png")
        self.assertEqual(body["examinationTypeName"], "MRI")
        self.assertEqual(body["time"], "09:00:00")
        self.assertEqual(body["totalAmount"], 40000.0)
        self.assertFalse(body["isLock"])
        exam = Examination.objects.get(pk=body["id"])
        self.assertEqual(exam.created_by, self.admin)
        self.assertEqual(exam.room, "204")

    def test_required_fields(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        expected = {"date", "time", "doctor", "examinationType", "totalAmount", "depositAmount"}
        self.assertEqual(set(response.json()), expected)

    def test_slot_conflict_with_active_examination(self):
        make_examination(doctor=self.doctor, examination_type=self.exam_type)
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("already taken", response.json()["date"][0])

    def test_slot_free_when_existing_is_deleted_or_other_time(self):
        make_examination(doctor=self.doctor, examination_type=self.exam_type, status=Status.DELETED)
        make_examination(doctor=self.doctor, examination_type=self.exam_type, time=datetime.time(10))
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)

    def test_full_update_of_same_slot_is_not_a_conflict(self):
        exam = make_examination(doctor=self.doctor, examination_type=self.exam_type)
        response = self.client.put(f"{self.url}{exam.pk}/", self.payload(room="9"), format="json")
        self.assertEqual(response.status_code, 200, response.content)
        exam.refresh_from_db()
        self.assertEqual(exam.room, "9")
        self.assertEqual(exam.updated_by, self.admin)

    def test_destroy_soft_deletes(self):
        exam = make_examination()
        self.assertEqual(self.client.delete(f"{self.url}{exam.pk}/").status_code, 204)
        exam.refresh_from_db()
        self.assertEqual(exam.status, Status.DELETED)
        listed = [row["id"] for row in self.results(self.client.get(self.url))]
        self.assertNotIn(exam.pk, listed)

    def test_booked_slot_cannot_be_deleted(self):
        locked = make_examination(is_lock=True)
        paid = make_examination()
        make_order(examination=paid, stage=OrderStage.PAID)
        cases = [(locked, "Түгжээтэй үзлэгийг устгах боломжгүй"),
                 (paid, "Төлбөр төлсөн захиалга байна, үзлэгийг устгах боломжгүй")]
        for exam, message in cases:
            with self.subTest(message=message):
                response = self.client.delete(f"{self.url}{exam.pk}/")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"message": message})
                exam.refresh_from_db()
                self.assertEqual(exam.status, Status.ACTIVE)

    def test_list_filters_by_related_field(self):
        mine = make_examination(doctor=self.doctor)
        make_examination(doctor=make_doctor(first_name="Other"))
        response = self.client.get(self.url, {"doctor.first_name": "Gerel"})
        self.assertEqual([row["id"] for row in self.results(response)], [mine.pk])

    def test_invalid_filter_or_sort_is_a_client_error(self):
        make_examination(doctor=self.doctor)
        cases = [
            ({"doctor.nope": "x"}, "message"),
            ({"doctor.id": "abc"}, "message"),
            ({"doctor.created_at": "not-a-date"}, "message"),
            ({"sort": "nope"}, "sort"),
            ({"sort": "-doctor__nope"}, "sort"),
        ]
        for query, key in cases:
            with self.subTest(query=query):
                response = self.client.get(self.url, query)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(key, response.json())

    def test_sort_by_related_field(self):
        first = make_examination(doctor=make_doctor(first_name="Zaya"))
        second = make_examination(doctor=make_doctor(first_name="Anu"))
        response = self.client.get(self.url, {"sort": "doctor__first_name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in self.results(response)], [second.pk, first.pk])

    def test_anonymous_cannot_create(self):
        self.client.force_authenticate(None)
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(Examination.objects.exists())


class AvailableExaminationsTests(AdminAPITestCase):
    url = "/examinations/available/"

    def test_parameter_validation(self):
        exam_type = make_examination_type()
        cases = [
            ({"examination_type": exam_type.pk}, "Date is required (YYYY-MM)"),
            ({"date": "2030-01"}, "Examination type is required"),
            ({"date": "2030", "examination_type": exam_type.pk}, "Invalid format. Use YYYY-MM"),
            ({"date": "abc-de", "examination_type": exam_type.pk}, "Invalid format. Use YYYY-MM"),
            ({"date": "2030-13", "examination_type": exam_type.pk}, "Invalid format. Use YYYY-MM"),
            ({"date": "2030-00", "examination_type": exam_type.pk}, "Invalid format. Use YYYY-MM"),
            ({"date": "2030-01", "examination_type": "abc"}, "Examination type must be an integer id"),
        ]
        for query, message in cases:
            with self.subTest(query=query):
                response = self.client.get(self.url, query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["message"], message)

    def test_counts_open_slots_per_day(self):
        exam_type = make_examination_type()
        doctor = make_doctor()
        other_day = datetime.date(2030, 1, 20)
        open_slots = [
            make_examination(date=DAY, time=datetime.time(hour), doctor=doctor, examination_type=exam_type)
            for hour in (9, 10)
        ]
        make_examination(date=other_day, doctor=doctor, examination_type=exam_type)
        make_examination(date=DAY, time=datetime.time(11), doctor=doctor,
                         examination_type=exam_type, is_lock=True)
        make_examination(date=DAY, time=datetime.time(12), doctor=doctor,
                         examination_type=exam_type, status=Status.DELETED)
        make_examination(date=DAY)
        make_examination(date=datetime.date(2030, 2, 1), doctor=doctor, examination_type=exam_type)
        self.client.force_authenticate(None)
        response = self.client.get(self.url, {"date": "2030-01", "examination_type": exam_type.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [{"date": "2030-01-10", "count": len(open_slots)}, {"date": "2030-01-20", "count": 1}],
        )

    def test_past_month_has_no_availability(self):
        exam = make_examination(date=datetime.date(2020, 1, 10))
        response = self.client.get(
            self.url, {"date": "2020-01", "examination_type": exam.examination_type_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


class ExaminationServiceTests(AdminAPITestCase):
    def setUp(self):
        super().setUp()
        self.request = SimpleNamespace(user=self.admin)
        self.pack = make_examination_pack()

    def test_lock_and_unlock_are_idempotent(self):
        exam = make_examination()
        for method, expected in ((ExaminationService.lock, True), (ExaminationService.unlock, False)):
            for _ in range(2):
                self.assertIs(method(exam.pk).is_lock, expected)
            exam.refresh_from_db()
            self.assertIs(exam.is_lock, expected)

    def test_lock_unknown_id_raises_404(self):
        for method in (ExaminationService.lock, ExaminationService.unlock, ExaminationService.get_by_id):
            with self.subTest(method=method.__name__), self.assertRaises(Http404):
                method(999999)

    def test_locked_queries_by_pack(self):
        locked = make_examination(examination_pack=self.pack, is_lock=True)
        make_examination(examination_pack=self.pack)
        make_examination(examination_pack=self.pack, is_lock=True, status=Status.DELETED)
        self.assertEqual([row["id"] for row in ExaminationService.get_locked_by_examination_pack(self.pack.pk)],
                         [locked.pk])
        self.assertTrue(ExaminationService.has_locked_by_examination_pack(self.pack.pk))
        ExaminationService.unlock(locked.pk)
        self.assertFalse(ExaminationService.has_locked_by_examination_pack(self.pack.pk))

    def test_exists_by_doctor_and_type_ignore_deleted(self):
        exam = make_examination(status=Status.DELETED)
        self.assertFalse(ExaminationService.exists_by_doctor(exam.doctor_id))
        self.assertFalse(ExaminationService.exists_by_examination_type(exam.examination_type_id))
        Examination.objects.filter(pk=exam.pk).update(status=Status.ACTIVE)
        self.assertTrue(ExaminationService.exists_by_doctor(exam.doctor_id))
        self.assertTrue(ExaminationService.exists_by_examination_type(exam.examination_type_id))

    def test_delete_and_delete_by_pack(self):
        single = make_examination()
        ExaminationService.delete(single.pk)
        single.refresh_from_db()
        self.assertEqual(single.status, Status.DELETED)
        in_pack = [make_examination(examination_pack=self.pack, time=datetime.time(h)) for h in (9, 10)]
        self.assertEqual(ExaminationService.delete_by_examination_pack(self.pack.pk), 2)
        self.assertEqual(
            set(Examination.objects.filter(pk__in=[e.pk for e in in_pack]).values_list("status", flat=True)),
            {Status.DELETED},
        )

    def test_create_update_and_get_all(self):
        doctor, exam_type = make_doctor(), make_examination_type()
        data = {"date": DAY, "time": "08:00", "doctor": doctor.pk, "examination_type": exam_type.pk,
                "total_amount": "100.00", "deposit_amount": "10.00"}
        created = ExaminationService.create(data, self.request)
        updated = ExaminationService.update(created["id"], {**data, "room": "1"}, self.request)
        self.assertEqual(updated["room"], "1")
        self.assertEqual(Examination.objects.get(pk=created["id"]).created_by, self.admin)
        self.assertEqual([row["id"] for row in ExaminationService.get_all()], [created["id"]])
        bulk = ExaminationService.create_bulk(
            [{**data, "time": "11:00"}, {**data, "time": "12:00"}], self.request
        )
        self.assertEqual([row["time"] for row in bulk], ["11:00:00", "12:00:00"])
