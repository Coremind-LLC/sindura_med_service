from rest_framework import serializers

from apps.doctor.models import Doctor
from apps.examination.models import Examination
from apps.examination_type.models import ExaminationType

class ExaminationSerializer(serializers.ModelSerializer):
    date = serializers.DateField(required=True)
    time = serializers.TimeField(required=True)
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), required=True
    )
    examination_type = serializers.PrimaryKeyRelatedField(
        queryset=ExaminationType.objects.all(), required=True
    )
    doctor_first_name = serializers.CharField(source="doctor.first_name", read_only=True)
    doctor_last_name = serializers.CharField(source="doctor.last_name", read_only=True)
    doctor_position = serializers.CharField(source="doctor.position", read_only=True)
    examination_type_name = serializers.CharField(
        source="examination_type.name", read_only=True
    )

    class Meta:
        model = Examination
        fields = "__all__"

# class ExaminationCreateUpdateSerializer(serializers.ModelSerializer):
#     dates = serializers.ListField(
#         child=serializers.DateField(),
#         required=True,
#         allow_empty=False
#     )
#     start_time = serializers.TimeField(required=True)
#     end_time = serializers.TimeField(required=True)
#     lunch_break_start_time = serializers.TimeField(required=True)
#     lunch_break_end_time = serializers.TimeField(required=True)
#     period = serializers.IntegerField(required=True, min_value=1, max_value=60)
#     doctor = serializers.PrimaryKeyRelatedField(
#         queryset=Doctor.objects.all(), required=True
#     )
#     examination_type = serializers.PrimaryKeyRelatedField(
#         queryset=ExaminationType.objects.all(), required=True
#     )
#
#     class Meta:
#         model = Examination
#         fields = [
#             "dates",
#             "start_time",
#             "end_time",
#             "lunch_break_start_time",
#             "lunch_break_end_time",
#             "period",
#             "doctor",
#             "examination_type",
#         ]
#
#     def create(self, validated_data):
#         dates = validated_data.pop("dates")
#         doctor = validated_data.pop("doctor")
#         examination_type = validated_data.pop("examination_type")
#         start_time = validated_data.pop("start_time")
#         end_time = validated_data.pop("end_time")
#         lunch_break_start_time = validated_data.pop("lunch_break_start_time")
#         lunch_break_end_time = validated_data.pop("lunch_break_end_time")
#         period = validated_data.pop("period")
#
#         all_examinations = []
#
#         for date in dates:
#             slot_datetime = datetime.combine(date, start_time)
#             end_datetime = datetime.combine(date, end_time)
#             lunch_start_datetime = datetime.combine(date, lunch_break_start_time)
#             lunch_end_datetime = datetime.combine(date, lunch_break_end_time)
#
#             while slot_datetime + timedelta(minutes=period) <= end_datetime:
#                 if lunch_start_datetime <= slot_datetime < lunch_end_datetime:
#                     slot_datetime = lunch_end_datetime
#                     continue
#
#                 exam = Examination.objects.create(
#                     doctor=doctor,
#                     examination_type=examination_type,
#                     date=date,
#                     time=slot_datetime.time(),
#                     created_by=self.context['request'].user,
#                     updated_by=self.context['request'].user,
#                     **validated_data
#                 )
#                 all_examinations.append(exam)
#                 slot_datetime += timedelta(minutes=period)
#
#         return all_examinations