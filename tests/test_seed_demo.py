import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.test import override_settings

from accounts.models import User
from applications.models import Application
from jobs.management.commands.seed_demo import CANDIDATES, EMPLOYERS, JOB_SPECS
from jobs.models import Job, Skill


@pytest.mark.django_db
def test_seed_demo_is_idempotent_and_realistic():
    call_command("seed_demo")
    call_command("seed_demo")

    assert User.objects.filter(email__in=EMPLOYERS).count() == 3
    assert User.objects.filter(email__in=CANDIDATES).count() == 8
    assert Skill.objects.count() == 27
    assert Job.all_objects.filter(title__in=[spec[0] for spec in JOB_SPECS]).count() == 16
    assert Application.objects.count() == 28
    assert set(Application.objects.values_list("status", flat=True)) == {
        "APPLIED",
        "SHORTLISTED",
        "REJECTED",
        "HIRED",
    }
    assert Job.all_objects.filter(deleted_at__isnull=False, is_active=False).count() == 2
    assert Job.all_objects.filter(location__icontains="Istanbul").exists()
    assert Job.all_objects.filter(location__icontains="Berlin").exists()

    distribution = dict(
        Application.objects.values("status")
        .annotate(total=Count("id"))
        .values_list("status", "total")
    )
    assert distribution == {"APPLIED": 13, "SHORTLISTED": 7, "REJECTED": 6, "HIRED": 2}


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_reset_preserves_non_seed_application_for_demo_candidate():
    call_command("seed_demo")

    candidate = User.objects.get(email="candidate1@example.com")
    external_employer = User.objects.create_user(
        "external-employer@example.com", "StrongPass123!", role=User.Role.EMPLOYER
    )
    external_job = Job.objects.create(
        employer=external_employer,
        title="Non-seed role",
        description="Created outside seed_demo",
        location="Remote",
        employment_type=Job.EmploymentType.CONTRACT,
    )
    external_application = Application.objects.create(candidate=candidate, job=external_job)
    managed_application = Application.objects.get(
        candidate=candidate,
        job__title="Senior Django Developer",
        job__employer__email="employer.istanbul@example.com",
    )
    managed_application.status = Application.Status.HIRED
    managed_application.cover_letter = "Changed outside the seed definition"
    managed_application.save(update_fields=["status", "cover_letter"])

    call_command("seed_demo", "--reset")

    assert Application.objects.filter(pk=external_application.pk).exists()
    reset_managed_application = Application.objects.get(
        candidate=candidate,
        job__title="Senior Django Developer",
        job__employer__email="employer.istanbul@example.com",
    )
    assert reset_managed_application.status == Application.Status.APPLIED
    assert reset_managed_application.cover_letter.startswith(
        "I am excited to contribute to this team. Demo application"
    )

    call_command("seed_demo")
    assert Application.objects.filter(pk=external_application.pk).exists()
    assert Application.objects.filter(candidate=candidate).count() == 5


@pytest.mark.django_db
def test_reset_is_rejected_when_debug_is_disabled():
    with override_settings(DEBUG=False), pytest.raises(CommandError, match="DEBUG=True"):
        call_command("seed_demo", "--reset")
