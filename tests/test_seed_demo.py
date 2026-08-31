import pytest
from django.core.management import call_command
from django.db.models import Count

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
