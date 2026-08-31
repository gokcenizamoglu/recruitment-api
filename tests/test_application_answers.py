import json

import pytest
from django.urls import reverse

from applications.models import Application, ApplicationAnswer
from jobs.models import ApplicationQuestion, Job
from tests.conftest import auth


def make_question(job, question_type="TEXT", **overrides):
    values = {
        "text": f"{question_type} question",
        "question_type": question_type,
        "required": False,
        "options": [],
    }
    values.update(overrides)
    question = ApplicationQuestion(job=job, **values)
    question.full_clean()
    question.save()
    return question


def submit(client, job, answers=None):
    payload = {"job": job.id}
    if answers is not None:
        payload["answers"] = answers
    return client.post(reverse("application-list"), payload, format="json")


@pytest.mark.django_db
def test_existing_application_shape_and_optional_questions_remain_compatible(
    api_client, candidate, job
):
    make_question(job, required=False)
    response = submit(auth(api_client, candidate), job)
    assert response.status_code == 201, response.data
    assert response.data["resume_available"] is False
    assert response.data["resume_download_url"] is None
    assert response.data["answers"] == []


@pytest.mark.django_db
def test_required_question_and_payload_membership_rules(
    api_client, candidate, job, employer, skill
):
    required = make_question(job, required=True)
    other_job = Job.objects.create(
        employer=employer,
        title="Another",
        description="Another",
        location="Remote",
        employment_type=Job.EmploymentType.FULL_TIME,
    )
    other_job.skills.add(skill)
    other_question = make_question(other_job)

    client = auth(api_client, candidate)
    assert submit(client, job).status_code == 400
    assert submit(client, job, [{"question": other_question.id, "value": "x"}]).status_code == 400
    duplicate = submit(
        client,
        job,
        [
            {"question": required.id, "value": "x"},
            {"question": required.id, "value": "y"},
        ],
    )
    assert duplicate.status_code == 400
    assert "Duplicate" in str(duplicate.data["answers"])


@pytest.mark.django_db
def test_inactive_question_cannot_be_answered(api_client, candidate, job):
    question = make_question(job, is_active=False)
    response = submit(auth(api_client, candidate), job, [{"question": question.id, "value": "x"}])
    assert response.status_code == 400
    assert "Inactive" in str(response.data["answers"])


@pytest.mark.django_db
def test_text_and_textarea_answers_are_validated_and_stored(api_client, candidate, job):
    text = make_question(job, "TEXT", required=True)
    textarea = make_question(job, "TEXTAREA", required=True)
    response = submit(
        auth(api_client, candidate),
        job,
        [
            {"question": text.id, "value": "  concise  "},
            {"question": textarea.id, "value": "  longer answer  "},
        ],
    )
    assert response.status_code == 201
    assert [answer["value"] for answer in response.data["answers"]] == ["concise", "longer answer"]


@pytest.mark.django_db
def test_strict_number_and_boolean_validation(api_client, candidate, job):
    number = make_question(job, "NUMBER", required=True)
    boolean = make_question(job, "BOOLEAN", required=True)
    client = auth(api_client, candidate)

    assert (
        submit(
            client,
            job,
            [{"question": number.id, "value": True}, {"question": boolean.id, "value": True}],
        ).status_code
        == 400
    )
    assert (
        submit(
            client,
            job,
            [{"question": number.id, "value": 5}, {"question": boolean.id, "value": "true"}],
        ).status_code
        == 400
    )
    valid = submit(
        client,
        job,
        [{"question": number.id, "value": 5.5}, {"question": boolean.id, "value": False}],
    )
    assert valid.status_code == 201
    assert [item["value"] for item in valid.data["answers"]] == [5.5, False]


@pytest.mark.django_db
def test_single_choice_must_match_configured_option(api_client, candidate, job):
    question = make_question(job, "SINGLE_CHOICE", required=True, options=["Remote", "On-site"])
    client = auth(api_client, candidate)
    invalid = submit(client, job, [{"question": question.id, "value": "Hybrid"}])
    assert invalid.status_code == 400

    valid = submit(client, job, [{"question": question.id, "value": "Remote"}])
    assert valid.status_code == 201
    answer = valid.data["answers"][0]
    assert answer["value"] == "Remote"
    assert answer["options"] == ["Remote", "On-site"]


@pytest.mark.django_db
def test_multipart_answers_json_string_is_atomic(api_client, candidate, job):
    question = make_question(job, "BOOLEAN", required=True)
    response = auth(api_client, candidate).post(
        reverse("application-list"),
        {"job": job.id, "answers": json.dumps([{"question": question.id, "value": True}])},
        format="multipart",
    )
    assert response.status_code == 201
    assert Application.objects.count() == 1
    assert ApplicationAnswer.objects.count() == 1


@pytest.mark.django_db
def test_question_history_uses_snapshots_and_type_change_is_blocked(
    api_client, candidate, employer, job
):
    question = make_question(job, "TEXT", required=True, text="Original wording")
    response = submit(
        auth(api_client, candidate), job, [{"question": question.id, "value": "Original answer"}]
    )
    assert response.status_code == 201
    application_id = response.data["id"]
    detail_url = reverse("job-question-detail", args=[job.id, question.id])

    changed = auth(api_client, employer).patch(
        detail_url, {"text": "Future wording"}, format="json"
    )
    assert changed.status_code == 200
    type_change = auth(api_client, employer).patch(
        detail_url, {"question_type": "NUMBER", "options": []}, format="json"
    )
    assert type_change.status_code == 400
    assert auth(api_client, employer).delete(detail_url).status_code == 204

    historical = auth(api_client, candidate).get(reverse("application-list"))
    answer = historical.data["results"][0]["answers"][0]
    assert historical.data["results"][0]["id"] == application_id
    assert answer["question_text"] == "Original wording"
    assert answer["question_type"] == "TEXT"
    assert ApplicationAnswer.objects.filter(question=question).exists()
