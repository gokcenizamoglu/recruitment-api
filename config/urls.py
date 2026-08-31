from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from accounts.views import LoginView, MeView, RefreshView, RegistrationView
from applications.views import ApplicationViewSet
from common.views import HealthCheckView
from jobs.question_views import ApplicationQuestionDetailView, ApplicationQuestionListCreateView
from jobs.views import JobViewSet, SkillViewSet

router = DefaultRouter()
router.register("skills", SkillViewSet, basename="skill")
router.register("jobs", JobViewSet, basename="job")
router.register("applications", ApplicationViewSet, basename="application")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/register/", RegistrationView.as_view(), name="register"),
    path("api/v1/auth/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", RefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/me/", MeView.as_view(), name="me"),
    path("api/v1/health/", HealthCheckView.as_view(), name="health"),
    path(
        "api/v1/jobs/<int:job_id>/questions/",
        ApplicationQuestionListCreateView.as_view(),
        name="job-question-list",
    ),
    path(
        "api/v1/jobs/<int:job_id>/questions/<int:question_id>/",
        ApplicationQuestionDetailView.as_view(),
        name="job-question-detail",
    ),
    path("api/v1/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
