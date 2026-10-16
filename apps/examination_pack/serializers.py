from datetime import date, datetime, time, timedelta
from typing import Any

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.common.enums import Status
from apps.common.serializers import BlankAsNullCharField
from apps.doctor.models import Doctor
from apps.examination.services import ExaminationService
from apps.examination_pack.models import ExaminationPack
from apps.examination_type.models import ExaminationType


def slot_times(
    day: date,
    start_time: time,
    end_time: time,
    period: int,
    lunch_start_time: time | None = None,
    lunch_end_time: time | None = None,
) -> list[time]:
    """Times of the ``period``-minute slots that fit in a working day, skipping lunch."""
    step = timedelta(minutes=period)
    slot = datetime.combine(day, start_time)
    end = datetime.combine(day, end_time)
    lunch_start = datetime.combine(day, lunch_start_time) if lunch_start_time else None
    lunch_end = datetime.combine(day, lunch_end_time) if lunch_end_time else None

    times = []
    while slot + step <= end:
        if lunch_start and lunch_end and lunch_start <= slot < lunch_end:
            slot = lunch_end
            continue
        times.append(slot.time())
        slot += step
    return times


def build_pack_examinations(pack: ExaminationPack) -> list[dict]:
    """Examination payloads for every slot of every date in the pack."""
    return [
        {
            "examination_pack": pack.id,
            "doctor": pack.doctor_id,
            "examination_type": pack.examination_type_id,
            "date": day,
            "time": slot,
            "total_amount": pack.total_amount,
            "deposit_amount": pack.deposit_amount,
            "room": pack.room,
        }
        for day in pack.dates
        for slot in slot_times(
            day,
            pack.start_time,
            pack.end_time,
            pack.period,
            pack.lunch_break_start_time,
            pack.lunch_break_end_time,
        )
    ]


class ExaminationPackSerializer(serializers.ModelSerializer):
    dates = serializers.ListField(
        child=serializers.DateField(),
        required=True
    )
    start_time = serializers.TimeField(required=True)
    end_time = serializers.TimeField(required=True)
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), required=True
    )
    examination_type = serializers.PrimaryKeyRelatedField(
        queryset=ExaminationType.objects.all(), required=True
    )
    period = serializers.IntegerField(required=True, min_value=1)
    total_amount = serializers.DecimalField(max_digits=20, decimal_places=2, required=True)
    deposit_amount = serializers.DecimalField(max_digits=20, decimal_places=2, required=True)
    room = BlankAsNullCharField(max_length=32)
    doctor_first_name = serializers.CharField(source="doctor.first_name", read_only=True)
    doctor_last_name = serializers.CharField(source="doctor.last_name", read_only=True)
    doctor_position = serializers.CharField(source="doctor.position", read_only=True)
    examination_type_name = serializers.CharField(
        source="examination_type.name", read_only=True
    )

    class Meta:
        model = ExaminationPack
        fields = "__all__"

    def validate(self, attrs) -> dict:
        doctor = attrs.get("doctor")
        examination_type = attrs.get("examination_type")
        dates = attrs.get("dates")

        if doctor and examination_type and dates:
            conflict = ExaminationPack.objects.filter(
                doctor=doctor,
                examination_type=examination_type,
                dates__overlap=dates,
                status=Status.ACTIVE
            )

            if self.instance:
                conflict = conflict.exclude(pk=self.instance.pk)

            if conflict.exists():
                overlapping_dates = sorted(
                    {d for pack in conflict for d in set(pack.dates) & set(dates)}
                )
                raise ValidationError({
                    "message": f"The following dates are already taken for this doctor and examination type: {overlapping_dates}"
                })

        self._validate_schedule(attrs)
        return attrs

    def _current(self, attrs: dict, name: str) -> Any:
        if name in attrs:
            return attrs[name]
        return getattr(self.instance, name, None)

    def _validate_schedule(self, attrs: dict) -> None:
        period = self._current(attrs, "period")
        if period is None or period < 1:
            raise ValidationError({"period": "Period must be a positive number of minutes."})

        lunch_start = self._current(attrs, "lunch_break_start_time")
        lunch_end = self._current(attrs, "lunch_break_end_time")
        if (lunch_start is None) != (lunch_end is None):
            raise ValidationError({
                "lunch_break_end_time" if lunch_end is None else "lunch_break_start_time":
                    "Lunch break start and end times must be given together."
            })
        if lunch_start is not None and lunch_end <= lunch_start:
            raise ValidationError(
                {"lunch_break_end_time": "Lunch break end time must be after its start time."}
            )

    @transaction.atomic
    def create(self, validated_data) -> ExaminationPack:
        request = self.context["request"]
        examination_pack = super().create(validated_data)
        ExaminationService.create_bulk(build_pack_examinations(examination_pack), request)
        return examination_pack

    @transaction.atomic
    def update(self, instance, validated_data) -> ExaminationPack:
        request = self.context["request"]

        if ExaminationService.has_locked_by_examination_pack(instance.id):
            raise serializers.ValidationError({"examination": "Cannot update this examination pack because it has locked examinations."})

        instance.dates = validated_data.get("dates", instance.dates)
        instance.start_time = validated_data.get("start_time", instance.start_time)
        instance.end_time = validated_data.get("end_time", instance.end_time)
        instance.lunch_break_start_time = validated_data.get("lunch_break_start_time", instance.lunch_break_start_time)
        instance.lunch_break_end_time = validated_data.get("lunch_break_end_time", instance.lunch_break_end_time)
        instance.period = validated_data.get("period", instance.period)
        instance.doctor = validated_data.get("doctor", instance.doctor)
        instance.examination_type = validated_data.get("examination_type", instance.examination_type)
        instance.total_amount = validated_data.get("total_amount", instance.total_amount)
        instance.deposit_amount = validated_data.get("deposit_amount", instance.deposit_amount)
        instance.room = validated_data.get("room", instance.room)

        instance.save()

        ExaminationService.delete_by_examination_pack(instance.id)
        ExaminationService.create_bulk(build_pack_examinations(instance), request)

        return instance
