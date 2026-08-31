import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint_reports_health_without_database_details(api_client):
    response = api_client.get(reverse("health"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] == "reachable"
    serialized = response.content.decode().lower()
    for sensitive_value in ("password", "postgresql://", "host", "username"):
        assert sensitive_value not in serialized
