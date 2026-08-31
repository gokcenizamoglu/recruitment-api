import pytest
from django.core.cache import cache
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


@pytest.mark.django_db
def test_refresh_rotation_blacklists_previous_token_and_me(api_client, candidate):
    login = api_client.post(
        reverse("token_obtain_pair"),
        {"email": candidate.email, "password": "StrongPass123!"},
        format="json",
    )
    assert login.status_code == 200
    old_refresh = login.data["refresh"]

    refreshed = api_client.post(reverse("token_refresh"), {"refresh": old_refresh}, format="json")
    assert refreshed.status_code == 200
    assert refreshed.data["refresh"] != old_refresh

    rejected = api_client.post(reverse("token_refresh"), {"refresh": old_refresh}, format="json")
    assert rejected.status_code == 401

    me = api_client.get(reverse("me"), HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
    assert me.status_code == 200
    assert me.data["email"] == candidate.email


@pytest.mark.django_db
def test_registration_throttle_returns_429_after_configured_limit(api_client):
    cache.clear()
    responses = [
        api_client.post(
            reverse("register"),
            {
                "email": f"throttle-{index}@example.com",
                "password": "StrongPass123!",
                "role": "CANDIDATE",
            },
            format="json",
        )
        for index in range(11)
    ]
    cache.clear()

    assert [response.status_code for response in responses[:10]] == [201] * 10
    assert responses[10].status_code == 429
