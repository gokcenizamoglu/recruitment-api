import pytest
from django.urls import reverse

from tests.conftest import auth


@pytest.mark.django_db
def test_application_rules(api_client, candidate, employer, employer2, job):
    endpoint = reverse("application-list")
    assert (
        auth(api_client, employer).post(endpoint, {"job": job.id}, format="json").status_code == 403
    )
    client = auth(api_client, candidate)
    assert (
        client.post(endpoint, {"job": job.id, "cover_letter": "Hello"}, format="json").status_code
        == 201
    )
    duplicate = client.post(endpoint, {"job": job.id}, format="json")
    assert duplicate.status_code == 400 and "job" in duplicate.data
    assert client.get(endpoint).data["count"] == 1
    app_id = client.get(endpoint).data["results"][0]["id"]
    assert auth(api_client, employer).get(reverse("application-list")).data["count"] == 1
    assert auth(api_client, employer2).get(reverse("application-list")).data["count"] == 0
    assert (
        auth(api_client, candidate)
        .patch(reverse("application-status", args=[app_id]), {"status": "HIRED"}, format="json")
        .status_code
        == 403
    )
    assert (
        auth(api_client, employer)
        .patch(
            reverse("application-status", args=[app_id]), {"status": "SHORTLISTED"}, format="json"
        )
        .status_code
        == 200
    )


@pytest.mark.django_db
def test_cannot_apply_inactive_or_deleted(api_client, candidate, job):
    job.is_active = False
    job.save(update_fields=["is_active"])
    response = auth(api_client, candidate).post(
        reverse("application-list"), {"job": job.id}, format="json"
    )
    assert response.status_code == 400 and response.data["job"][0].code == "inactive_job"
