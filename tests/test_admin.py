import pytest
from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import Client, RequestFactory
from django.utils import timezone

from accounts.models import User
from applications.admin import ApplicationAdmin
from applications.models import Application
from common.admin import dashboard_callback
from jobs.admin import JobAdmin
from jobs.models import Job


@pytest.mark.django_db
def test_job_admin_includes_deleted_jobs_and_restore(job, employer):
    job.deleted_at = timezone.now()
    job.is_active = False
    job.save(update_fields=["deleted_at", "is_active"])
    model_admin = JobAdmin(Job, admin.site)
    request = RequestFactory().get("/admin/")
    request.user = employer
    request.session = {}
    request._messages = FallbackStorage(request)
    queryset = model_admin.get_queryset(request)
    assert queryset.filter(pk=job.pk).exists()
    model_admin.restore_selected(request, queryset.filter(pk=job.pk))
    job.refresh_from_db()
    assert job.deleted_at is None and job.is_active is True


@pytest.mark.django_db
def test_application_admin_preserves_history(candidate, job):
    application = Application.objects.create(candidate=candidate, job=job)
    model_admin = ApplicationAdmin(Application, admin.site)
    request = RequestFactory().get("/admin/")
    request.user = candidate
    assert model_admin.has_delete_permission(request, application) is False


@pytest.mark.django_db
def test_dashboard_metrics_and_status_counts(candidate, employer, job):
    Application.objects.create(candidate=candidate, job=job)
    request = RequestFactory().get("/admin/")
    request.user = employer
    context = dashboard_callback(request, {})
    assert context["recruitment_metrics"]["employers"] == 1
    assert context["recruitment_metrics"]["candidates"] == 1
    assert context["recruitment_metrics"]["applications"] == 1


@pytest.mark.django_db
def test_unfold_admin_dashboard_renders():
    user = User.objects.create_superuser(
        "admin@example.com", "StrongPass123!", role=User.Role.EMPLOYER
    )
    client = Client()
    assert client.force_login(user) is None
    response = client.get("/admin/")
    assert response.status_code == 200
    assert b"Recruitment Administration" in response.content
