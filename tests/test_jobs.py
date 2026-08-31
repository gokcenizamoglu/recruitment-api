import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from jobs.models import Skill
from tests.conftest import auth


@pytest.mark.django_db
def test_job_permissions_and_soft_delete(api_client, employer, employer2, candidate, skill):
    payload = {
        "title": "Backend",
        "description": "Python API",
        "location": "Remote",
        "employment_type": "FULL_TIME",
        "skill_ids": [skill.id],
    }
    assert (
        auth(api_client, candidate).post(reverse("job-list"), payload, format="json").status_code
        == 403
    )
    created = auth(api_client, employer).post(reverse("job-list"), payload, format="json")
    assert created.status_code == 201
    job_id = created.data["id"]
    assert (
        auth(api_client, employer2)
        .patch(reverse("job-detail", args=[job_id]), {"title": "Nope"}, format="json")
        .status_code
        == 404
    )
    assert (
        auth(api_client, employer).delete(reverse("job-detail", args=[job_id])).status_code == 204
    )
    assert auth(api_client, candidate).get(reverse("job-list")).json()["count"] == 0


@pytest.mark.django_db
def test_candidate_can_search_and_filter(api_client, candidate, job):
    response = auth(api_client, candidate).get(
        reverse("job-list"),
        {"search": "Django", "location": "Remote", "employment_type": "FULL_TIME"},
    )
    assert response.status_code == 200 and response.data["count"] == 1


@pytest.mark.django_db
def test_other_employer_cannot_put_an_owned_job(api_client, employer, employer2, job, skill):
    response = auth(api_client, employer2).put(
        reverse("job-detail", args=[job.id]),
        {
            "title": "Unauthorized replacement",
            "description": "Should not be accepted",
            "location": "Remote",
            "employment_type": "FULL_TIME",
            "skill_ids": [skill.id],
        },
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_other_employer_cannot_patch_an_owned_job(api_client, employer2, job):
    response = auth(api_client, employer2).patch(
        reverse("job-detail", args=[job.id]), {"title": "Unauthorized"}, format="json"
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_other_employer_cannot_delete_an_owned_job(api_client, employer2, job):
    response = auth(api_client, employer2).delete(reverse("job-detail", args=[job.id]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_candidate_cannot_apply_to_deleted_job(api_client, candidate, job):
    job.soft_delete()
    response = auth(api_client, candidate).post(
        reverse("application-list"), {"job": job.id}, format="json"
    )
    assert response.status_code == 400
    assert response.data["job"][0].code == "inactive_job"


@pytest.mark.django_db
def test_skill_semantic_duplicates_are_normalized_and_unique(db):
    first = Skill.objects.create(name="  Python ")
    assert first.name == "python"

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Skill.objects.create(name="PYTHON")

    assert Skill.objects.filter(name="python").count() == 1
