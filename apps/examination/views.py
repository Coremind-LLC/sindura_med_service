from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.examination.models import Examination
from apps.examination.serializers import ExaminationSerializer, ExaminationCreateUpdateSerializer

class ExaminationViewSet(BaseViewSet):
    queryset = Examination.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return ExaminationCreateUpdateSerializer
        return ExaminationSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        examinations = serializer.save()

        output_serializer = ExaminationSerializer(examinations, many=True)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)