from datetime import datetime, timedelta

from django.db import transaction
from rest_framework import serializers

from apps.doctor.models import Doctor
from apps.examination.services import ExaminationService
from apps.examination_pack.models import ExaminationPack
from apps.examination_type.models import ExaminationType

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
    period = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, required=True)
    doctor_first_name = serializers.CharField(source="doctor.first_name", read_only=True)
    doctor_last_name = serializers.CharField(source="doctor.last_name", read_only=True)
    doctor_position = serializers.CharField(source="doctor.position", read_only=True)
    examination_type_name = serializers.CharField(
        source="examination_type.name", read_only=True
    )

    class Meta:
        model = ExaminationPack
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        examination_pack = super().create(validated_data)

        dates = validated_data["dates"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]
        lunch_break_start_time = validated_data.get("lunch_break_start_time")
        lunch_break_end_time = validated_data.get("lunch_break_end_time")
        period = validated_data.get("period")
        doctor = validated_data.get("doctor")
        examination_type = validated_data.get("examination_type")
        amount = validated_data.get("amount")

        examinations = []

        for date in dates:
            slot_datetime = datetime.combine(date, start_time)
            end_datetime = datetime.combine(date, end_time)
            lunch_break_start_datetime = datetime.combine(date, lunch_break_start_time)
            lunch_break_end_datetime = datetime.combine(date, lunch_break_end_time)

            while slot_datetime + timedelta(minutes=period) <= end_datetime:
                if lunch_break_start_datetime <= slot_datetime < lunch_break_end_datetime:
                    slot_datetime = lunch_break_end_datetime
                    continue

                examinations.append({
                    "examination_pack": examination_pack.id,
                    "doctor": doctor.id,
                    "examination_type": examination_type.id,
                    "date": date,
                    "time": slot_datetime.time(),
                    "amount": amount,
                })

                slot_datetime += timedelta(minutes=period)

        ExaminationService.create_bulk(examinations, request)

        return examination_pack

    @transaction.atomic
    def update(self, instance, validated_data):
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
        instance.amount = validated_data.get("amount", instance.amount)

        instance.save()

        ExaminationService.delete_by_examination_pack(instance.id)

        dates = instance.dates
        start_time = instance.start_time
        end_time = instance.end_time
        lunch_start_time = instance.lunch_break_start_time
        lunch_end_time = instance.lunch_break_end_time
        period = instance.period
        doctor = instance.doctor
        examination_type = instance.examination_type
        amount = instance.amount

        examinations = []

        for date in dates:
            slot_datetime = datetime.combine(date, start_time)
            end_datetime = datetime.combine(date, end_time)
            lunch_start = (
                datetime.combine(date, lunch_start_time) if lunch_start_time else None
            )
            lunch_end = (
                datetime.combine(date, lunch_end_time) if lunch_end_time else None
            )

            while slot_datetime + timedelta(minutes=period) <= end_datetime:
                if lunch_start and lunch_start <= slot_datetime < lunch_end:
                    slot_datetime = lunch_end
                    continue

                examinations.append({
                    "examination_pack": instance.id,
                    "doctor": doctor.id,
                    "examination_type": examination_type.id,
                    "date": date,
                    "time": slot_datetime.time(),
                    "amount": amount,
                })

                slot_datetime += timedelta(minutes=period)

        ExaminationService.create_bulk(examinations, request)

        return instance