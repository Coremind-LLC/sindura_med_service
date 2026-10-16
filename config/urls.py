from django.conf import settings
from django.urls import path, include, re_path
from django.views.static import serve

from rest_framework.routers import DefaultRouter
from rest_framework.permissions import AllowAny

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from apps.activity_log.views import ActivityLogViewSet
from apps.auth.views import AuthViewSet
from apps.doctor.views import DoctorViewSet
from apps.examination.views import ExaminationViewSet
from apps.examination_pack.views import ExaminationPackViewSet
from apps.examination_type.views import ExaminationTypeViewSet
from apps.file.views import FileViewSet
from apps.invoice.views import InvoiceViewSet
from apps.order.views import OrderViewSet
from apps.payment.views import PaymentViewSet
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
router.register(r"examination-packs", ExaminationPackViewSet)
router.register(r"examination-types", ExaminationTypeViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"invoices", InvoiceViewSet)
router.register(r"activity-logs", ActivityLogViewSet)
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"files", FileViewSet, basename="file")
router.register(r"auth", AuthViewSet, basename="auth")

urlpatterns = [
    path("", include(router.urls)),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0)),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0)),
]

# Uploaded images (doctor photos, type icons) are served by Django unless a proxy does it.
if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(rf"^{settings.MEDIA_URL.lstrip('/')}(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
