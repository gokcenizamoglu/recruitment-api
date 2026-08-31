from django.db.models import Count
from django.urls import reverse

from accounts.models import User
from applications.models import Application
from jobs.models import Job


def dashboard_callback(request, context):
    context["recruitment_metrics"] = {
        "employers": User.objects.filter(role=User.Role.EMPLOYER).count(),
        "candidates": User.objects.filter(role=User.Role.CANDIDATE).count(),
        "jobs": Job.all_objects.filter(deleted_at__isnull=True).count(),
        "active_jobs": Job.objects.filter(is_active=True).count(),
        "applications": Application.objects.count(),
    }
    context["application_status_counts"] = list(
        Application.objects.values("status").annotate(total=Count("id")).order_by("status")
    )
    context["recent_applications"] = Application.objects.select_related(
        "candidate", "job", "job__employer"
    ).order_by("-created_at", "-id")[:8]
    context["application_admin_url"] = reverse("admin:applications_application_changelist")
    return context
