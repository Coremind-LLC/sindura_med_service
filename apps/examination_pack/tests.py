import datetime
from types import SimpleNamespace

from apps.common.enums import Status
from apps.examination.models import Examination
from apps.examination_pack.models import ExaminationPack
from apps.examination_pack.serializers import slot_times
from apps.examination_pack.services import ExaminationPackService
from helpers.tests_factories import (
    AdminAPITestCase,
    make_doctor,
    make_examination,
    make_examination_pack,
    make_examination_type,
)


class PackTestMixin:
    url = "/examination-packs/"

    def setUp(self):
        super().setUp()
        self.doctor = make_doctor()
        self.exam_type = make_examination_type()
        self.request = SimpleNamespace(user=self.admin)

    def pack_payload(self, **overrides):
        data = {
            "dates": ["2030-03-01", "2030-03-02"],
            "startTime": "09:00",
            "endTime": "12:00",
            "lunchBreakStartTime": "10:00",
            "lunchBreakEndTime": "11:00",
            "period": 30,
            "doctor": self.doctor.pk,
            "examinationType": self.exam_type.pk,
            "totalAmount": "60000.00",
            "depositAmount": "15000.00",
            "room": "101",
        }
        data.update(overrides)
        return data

    def active_slots(self, pack_id):
        rows = Examination.objects.filter(examination_pack_id=pack_id, status=Status.ACTIVE)
        return sorted((e.date.isoformat(), e.time.strftime("%H:%M")) for e in rows)


class ExaminationPackCreateTests(PackTestMixin, AdminAPITestCase):
    def test_create_generates_slots_around_lunch_break(self):
        response = self.client.post(self.url, self.pack_payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["doctorFirstName"], self.doctor.first_name)
        self.assertEqual(body["examinationTypeName"], self.exam_type.name)
        times = ["09:00", "09:30", "11:00", "11:30"]
        expected = sorted((d, t) for d in ("2030-03-01", "2030-03-02") for t in times)
        self.assertEqual(self.active_slots(body["id"]), expected)
        exam = Examination.objects.filter(examination_pack_id=body["id"]).first()
        self.assertEqual((exam.room, exam.doctor, exam.created_by), ("101", self.doctor, self.admin))
        self.assertEqual(str(exam.total_amount), "60000.00")

    def test_slot_generation_table(self):
        cases = [
            ({"lunchBreakStartTime": "10:15", "lunchBreakEndTime": "11:00"},
             ["09:00", "09:30", "10:00", "11:00", "11:30"]),
            ({"endTime": "10:00", "period": 25}, ["09:00", "09:25"]),
            ({"startTime": "13:00", "endTime": "15:00", "period": 60}, ["13:00", "14:00"]),
            ({"endTime": "09:20", "period": 30}, []),
        ]
        for index, (overrides, times) in enumerate(cases):
            day = f"2030-04-{index + 1:02d}"
            with self.subTest(overrides=overrides):
                payload = self.pack_payload(dates=[day], **overrides)
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, 201, response.content)
                self.assertEqual(self.active_slots(response.json()["id"]), [(day, t) for t in times])

    def test_create_without_lunch_break_generates_slots_straight_through(self):
        straight = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"]
        variants = [
            {"lunchBreakStartTime": None, "lunchBreakEndTime": None},
            "omitted",
        ]
        for index, variant in enumerate(variants):
            day = f"2030-09-{index + 1:02d}"
            payload = self.pack_payload(dates=[day])
            if variant == "omitted":
                del payload["lunchBreakStartTime"], payload["lunchBreakEndTime"]
            else:
                payload.update(variant)
            with self.subTest(variant=variant):
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, 201, response.content)
                self.assertIsNone(response.json()["lunchBreakStartTime"])
                self.assertEqual(self.active_slots(response.json()["id"]),
                                 [(day, t) for t in straight])

    def test_invalid_schedule_is_rejected(self):
        cases = [
            ({"lunchBreakEndTime": None}, "lunchBreakEndTime"),
            ({"lunchBreakStartTime": None}, "lunchBreakStartTime"),
            ({"lunchBreakStartTime": "11:00", "lunchBreakEndTime": "10:00"}, "lunchBreakEndTime"),
            ({"lunchBreakStartTime": "11:00", "lunchBreakEndTime": "11:00"}, "lunchBreakEndTime"),
            ({"period": 0}, "period"),
            ({"period": -15}, "period"),
        ]
        for overrides, field in cases:
            with self.subTest(overrides=overrides):
                response = self.client.post(self.url, self.pack_payload(**overrides), format="json")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.json())
        self.assertFalse(ExaminationPack.objects.exists())
        self.assertFalse(Examination.objects.exists())

    def test_slot_times_helper(self):
        day = datetime.date(2030, 1, 1)
        nine, noon = datetime.time(9), datetime.time(12)
        self.assertEqual(slot_times(day, nine, noon, 60),
                         [datetime.time(9), datetime.time(10), datetime.time(11)])
        self.assertEqual(slot_times(day, nine, noon, 60, datetime.time(10), datetime.time(11)),
                         [datetime.time(9), datetime.time(11)])
        self.assertEqual(slot_times(day, nine, noon, 60, datetime.time(10), None),
                         [datetime.time(9), datetime.time(10), datetime.time(11)])

    def test_overlapping_dates_for_same_doctor_and_type_are_rejected(self):
        make_examination_pack(doctor=self.doctor, examination_type=self.exam_type,
                              dates=[datetime.date(2030, 3, 2)])
        response = self.client.post(self.url, self.pack_payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("2030, 3, 2", str(response.json()["message"]))
        self.assertEqual(ExaminationPack.objects.count(), 1)
        self.assertFalse(Examination.objects.exists())

    def test_overlap_ignores_deleted_packs_and_other_doctors(self):
        day = datetime.date(2030, 3, 1)
        make_examination_pack(doctor=self.doctor, examination_type=self.exam_type,
                              dates=[day], status=Status.DELETED)
        make_examination_pack(examination_type=self.exam_type, dates=[day])
        response = self.client.post(self.url, self.pack_payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)

    def test_required_fields(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        for field in ("dates", "startTime", "endTime", "period", "doctor", "examinationType"):
            self.assertIn(field, response.json())

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
        response = self.client.post(self.url, self.pack_payload(), format="json")
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(ExaminationPack.objects.exists())


class ExaminationPackChangeTests(PackTestMixin, AdminAPITestCase):
    def setUp(self):
        super().setUp()
        response = self.client.post(self.url, self.pack_payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.pack = ExaminationPack.objects.get(pk=response.json()["id"])
        self.detail = f"{self.url}{self.pack.pk}/"

    def lock_first_examination(self):
        exam = Examination.objects.filter(examination_pack=self.pack).first()
        Examination.objects.filter(pk=exam.pk).update(is_lock=True)

    def test_update_regenerates_examinations(self):
        payload = self.pack_payload(dates=["2030-05-05"], period=60, room="7",
                                    lunchBreakStartTime=None, lunchBreakEndTime=None)
        response = self.client.put(self.detail, payload, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        expected = [("2030-05-05", t) for t in ("09:00", "10:00", "11:00")]
        self.assertEqual(self.active_slots(self.pack.pk), expected)
        self.assertEqual(
            Examination.objects.filter(examination_pack=self.pack, status=Status.DELETED).count(), 8
        )
        self.pack.refresh_from_db()
        self.assertEqual((self.pack.room, self.pack.period), ("7", 60))

    def test_partial_update_validates_lunch_break_against_stored_values(self):
        cases = [
            ({"lunchBreakStartTime": None}, "lunchBreakStartTime"),
            ({"lunchBreakEndTime": "09:30"}, "lunchBreakEndTime"),
        ]
        for payload, field in cases:
            with self.subTest(payload=payload):
                response = self.client.patch(self.detail, payload, format="json")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.json())
        self.assertEqual(len(self.active_slots(self.pack.pk)), 8)

    def test_partial_update_clearing_lunch_break(self):
        payload = {"lunchBreakStartTime": None, "lunchBreakEndTime": None}
        response = self.client.patch(self.detail, payload, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(self.active_slots(self.pack.pk)), 12)

    def test_list_rejects_malformed_dates(self):
        response = self.client.get(self.url, {"dates": ["03/01/2030"]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["dates"], ["Invalid date format"])

    def test_update_blocked_by_locked_examination(self):
        self.lock_first_examination()
        response = self.client.put(self.detail, self.pack_payload(period=60), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("locked examinations", str(response.json()["examination"]))
        self.pack.refresh_from_db()
        self.assertEqual(self.pack.period, 30)
        self.assertEqual(len(self.active_slots(self.pack.pk)), 8)

    def test_destroy_soft_deletes_pack_and_examinations(self):
        self.assertEqual(self.client.delete(self.detail).status_code, 204)
        self.pack.refresh_from_db()
        self.assertEqual(self.pack.status, Status.DELETED)
        self.assertEqual(self.active_slots(self.pack.pk), [])
        self.assertEqual(self.results(self.client.get(self.url)), [])

    def test_destroy_blocked_by_locked_examination(self):
        self.lock_first_examination()
        response = self.client.delete(self.detail)
        self.assertEqual(response.status_code, 400)
        self.assertIn("locked examinations", response.json()["detail"])
        self.pack.refresh_from_db()
        self.assertEqual(self.pack.status, Status.ACTIVE)
        self.assertEqual(len(self.active_slots(self.pack.pk)), 8)

    def test_list_filters_by_dates(self):
        other = make_examination_pack(dates=[datetime.date(2030, 6, 1)])
        cases = [
            (["2030-03-02"], [self.pack.pk]),
            (["2030-06-01", "2030-03-01"], [other.pk, self.pack.pk]),
            (["2031-01-01"], []),
            ([], [other.pk, self.pack.pk]),
        ]
        for dates, expected in cases:
            with self.subTest(dates=dates):
                response = self.client.get(self.url, {"dates": dates})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([row["id"] for row in self.results(response)], expected)


class ExaminationPackServiceTests(PackTestMixin, AdminAPITestCase):
    def test_search_by_dates(self):
        pack = make_examination_pack(dates=[datetime.date(2030, 7, 1)])
        make_examination_pack(dates=[datetime.date(2030, 7, 1)], status=Status.DELETED)
        self.assertEqual(list(ExaminationPackService.search_by_dates(["2030-07-01"])), [pack])
        self.assertEqual(list(ExaminationPackService.search_by_dates([])), [pack])
        with self.assertRaisesMessage(ValueError, "Invalid date format"):
            ExaminationPackService.search_by_dates(["07/01/2030"])

    def test_exists_lookups_ignore_deleted(self):
        pack = make_examination_pack(status=Status.DELETED)
        self.assertFalse(ExaminationPackService.exists_by_doctor(pack.doctor_id))
        self.assertFalse(ExaminationPackService.exists_by_examination_type(pack.examination_type_id))
        make_examination_pack(doctor=pack.doctor, examination_type=pack.examination_type)
        self.assertTrue(ExaminationPackService.exists_by_doctor(pack.doctor_id))
        self.assertTrue(ExaminationPackService.exists_by_examination_type(pack.examination_type_id))

    def test_create_update_get_and_delete(self):
        data = {
            "dates": ["2030-08-01"], "start_time": "09:00", "end_time": "10:00",
            "lunch_break_start_time": "12:00", "lunch_break_end_time": "13:00", "period": 30,
            "doctor": self.doctor.pk, "examination_type": self.exam_type.pk,
            "total_amount": "1.00", "deposit_amount": "1.00",
        }
        created = ExaminationPackService.create(data, self.request)
        self.assertEqual(len(self.active_slots(created["id"])), 2)
        updated = ExaminationPackService.update(created["id"], {**data, "period": 60}, self.request)
        self.assertEqual(updated["period"], 60)
        self.assertEqual(ExaminationPackService.get_by_id(created["id"])["dates"], ["2030-08-01"])
        self.assertEqual([row["id"] for row in ExaminationPackService.get_all()], [created["id"]])
        ExaminationPackService.delete(created["id"])
        self.assertEqual(ExaminationPack.objects.get(pk=created["id"]).status, Status.DELETED)

    def test_locked_examination_of_other_pack_does_not_block(self):
        pack = make_examination_pack()
        make_examination(examination_pack=make_examination_pack(), is_lock=True)
        response = self.client.delete(f"{self.url}{pack.pk}/")
        self.assertEqual(response.status_code, 204)
