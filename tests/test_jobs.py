import pytest
from django.urls import reverse

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
