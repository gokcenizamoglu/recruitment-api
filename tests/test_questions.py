import pytest
from django.urls import reverse

from jobs.models import ApplicationQuestion, Job
from tests.conftest import auth


def question_payload(**overrides):
    payload = {
        "text": "Years of relevant experience?",
        "question_type": "NUMBER",
        "required": True,
        "order": 0,
        "options": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_employer_creates_questions_only_for_own_job(
    api_client, employer, employer2, candidate, job, skill
):
    other_job = Job.objects.create(
        employer=employer2,
        title="Other job",
        description="Other",
        location="Remote",
        employment_type=Job.EmploymentType.FULL_TIME,
    )
    other_job.skills.add(skill)

    own = auth(api_client, employer).post(
        reverse("job-question-list", args=[job.id]), question_payload(), format="json"
    )
    assert own.status_code == 201
    assert "job" not in own.data
    assert (
        auth(api_client, employer)
        .post(reverse("job-question-list", args=[other_job.id]), {}, format="json")
        .status_code
        == 404
    )
    assert (
        auth(api_client, candidate)
        .post(reverse("job-question-list", args=[job.id]), {}, format="json")
        .status_code
        == 403
    )


@pytest.mark.django_db
def test_question_visibility_and_candidate_write_denials(api_client, employer, candidate, job):
    active = ApplicationQuestion.objects.create(
        job=job, text="Active?", question_type="BOOLEAN", is_active=True
    )
    inactive = ApplicationQuestion.objects.create(
        job=job, text="Inactive?", question_type="BOOLEAN", is_active=False
    )
    list_url = reverse("job-question-list", args=[job.id])

    candidate_list = auth(api_client, candidate).get(list_url)
    assert candidate_list.status_code == 200
    assert [item["id"] for item in candidate_list.data] == [active.id]
    owner_list = auth(api_client, employer).get(list_url)
    assert {item["id"] for item in owner_list.data} == {active.id, inactive.id}

    detail = reverse("job-question-detail", args=[job.id, active.id])
    assert (
        auth(api_client, candidate).patch(detail, {"text": "No"}, format="json").status_code == 403
    )
    assert auth(api_client, candidate).delete(detail).status_code == 403


@pytest.mark.django_db
def test_other_employer_cannot_update_or_deactivate_question(api_client, employer2, job):
    question = ApplicationQuestion.objects.create(job=job, text="Owned", question_type="TEXT")
    url = reverse("job-question-detail", args=[job.id, question.id])

    assert auth(api_client, employer2).patch(url, {"text": "No"}, format="json").status_code == 404
    assert auth(api_client, employer2).delete(url).status_code == 404
    question.refresh_from_db()
    assert question.is_active is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "options",
    ["not-a-list", ["only one"], ["A", "A"], ["A", "  "], ["A", 2]],
)
def test_single_choice_options_are_strictly_validated(api_client, employer, job, options):
    response = auth(api_client, employer).post(
        reverse("job-question-list", args=[job.id]),
        question_payload(question_type="SINGLE_CHOICE", options=options),
        format="json",
    )
    assert response.status_code == 400
    assert "options" in response.data


@pytest.mark.django_db
def test_single_choice_options_are_normalized_and_scalar_options_rejected(
    api_client, employer, job
):
    list_url = reverse("job-question-list", args=[job.id])
    choice = auth(api_client, employer).post(
        list_url,
        question_payload(question_type="SINGLE_CHOICE", options=[" Remote ", "On-site"]),
        format="json",
    )
    assert choice.status_code == 201
    assert choice.data["options"] == ["Remote", "On-site"]

    scalar = auth(api_client, employer).post(
        list_url, question_payload(question_type="TEXT", options=["No"]), format="json"
    )
    assert scalar.status_code == 400
