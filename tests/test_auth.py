import pytest
from django.urls import reverse

from accounts.models import User


@pytest.mark.django_db
def test_registration_and_login(api_client):
    response = api_client.post(
        reverse("register"),
        {"email": "e@example.com", "password": "StrongPass123!", "role": "EMPLOYER"},
        format="json",
    )
    assert response.status_code == 201
    login = api_client.post(
        reverse("token_obtain_pair"),
        {"email": "e@example.com", "password": "StrongPass123!"},
        format="json",
    )
    assert login.status_code == 200 and "access" in login.data


@pytest.mark.django_db
def test_candidate_registration_and_invalid_registration(api_client):
    assert (
        api_client.post(
            reverse("register"),
            {"email": "c@example.com", "password": "StrongPass123!", "role": "CANDIDATE"},
            format="json",
        ).status_code
        == 201
    )
    invalid = api_client.post(
        reverse("register"), {"email": "bad", "password": "x", "role": "INVALID"}, format="json"
    )
    assert invalid.status_code == 400


@pytest.mark.django_db
def test_user_cannot_change_role(api_client, candidate):
    api_client.force_authenticate(user=candidate)
    response = api_client.patch(reverse("me"), {"role": "EMPLOYER"}, format="json")
    assert response.status_code in {405, 400}
    candidate.refresh_from_db()
    assert candidate.role == User.Role.CANDIDATE
