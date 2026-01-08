from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from rest_framework.permissions import AllowAny

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from apps.auth.views import AuthViewSet
from apps.doctor.views import DoctorViewSet
from apps.examination.views import ExaminationViewSet
from apps.examination_type.views import ExaminationTypeViewSet
from apps.order.views import OrderViewSet
from apps.user.views import UserViewSet


schema_view = get_schema_view(
    openapi.Info(
        title="Sindura Med API",
        default_version="v1",
        description="API documentation",
    ),
    public=True,
    permission_classes=[AllowAny],
)

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"doctors", DoctorViewSet)
router.register(r"examinations", ExaminationViewSet)
router.register(r"examination-types", ExaminationTypeViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"auth", AuthViewSet, basename="auth")

urlpatterns = [
    path("", include(router.urls)),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0)),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
