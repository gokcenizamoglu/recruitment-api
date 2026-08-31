import pytest
from rest_framework.test import APIClient

from accounts.models import User
from jobs.models import Job, Skill


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def employer(db):
    return User.objects.create_user(
        "employer@example.com", "StrongPass123!", role=User.Role.EMPLOYER
    )


@pytest.fixture
def employer2(db):
    return User.objects.create_user("other@example.com", "StrongPass123!", role=User.Role.EMPLOYER)


@pytest.fixture
def candidate(db):
    return User.objects.create_user(
        "candidate@example.com", "StrongPass123!", role=User.Role.CANDIDATE
    )


@pytest.fixture
def skill(db):
    return Skill.objects.create(name="Python")


@pytest.fixture
def job(employer, skill):
    item = Job.objects.create(
        employer=employer,
        title="Django Engineer",
        description="Build APIs",
        location="Remote",
        employment_type=Job.EmploymentType.FULL_TIME,
    )
    item.skills.add(skill)
    return item


def auth(client, user):
    client.force_authenticate(user=user)
    return client
