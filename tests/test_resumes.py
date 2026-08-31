import io
import json
import re
import zipfile

import pytest
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from applications.models import Application, ApplicationAnswer
from applications.validators import MAX_RESUME_SIZE, OLE_SIGNATURE
from tests.conftest import auth


def resume_file(kind="pdf", name=None, content_type=None):
    if kind == "pdf":
        content = b"%PDF-1.7\nminimal resume"
        default_type = "application/pdf"
    elif kind == "doc":
        content = OLE_SIGNATURE + b"minimal legacy document"
        default_type = "application/msword"
    else:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("word/document.xml", "<document />")
        content = buffer.getvalue()
        default_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return SimpleUploadedFile(
        name or f"resume.{kind}", content, content_type=content_type or default_type
    )


def zip_upload(name, entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.fixture
def private_storage(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    }
    return storages["default"]


def stored_files(storage, directory=""):
    directories, files = storage.listdir(directory)
    result = {f"{directory}/{name}".lstrip("/") for name in files}
    for child in directories:
        child_directory = f"{directory}/{child}".lstrip("/")
        result.update(stored_files(storage, child_directory))
    return result


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["pdf", "doc", "docx"])
def test_valid_resume_formats_are_stored_privately(
    api_client, candidate, job, private_storage, kind
):
    response = auth(api_client, candidate).post(
        reverse("application-list"),
        {"job": job.id, "resume": resume_file(kind)},
        format="multipart",
    )

    assert response.status_code == 201
    application = Application.objects.get()
    assert application.resume.name.startswith("resumes/")
    assert re.search(rf"/[0-9a-f]{{32}}\.{kind}$", application.resume.name)
    assert response.data["resume_available"] is True
    assert response.data["resume_download_url"] == reverse(
        "application-resume", args=[application.id]
    )
    serialized = str(response.data)
    assert "private_media" not in serialized
    assert application.resume.name not in serialized


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("uploaded", "error_code"),
    [
        (
            SimpleUploadedFile("resume.exe", b"MZ", content_type="application/octet-stream"),
            "invalid_resume_extension",
        ),
        (
            SimpleUploadedFile("resume.pdf", b"MZ", content_type="application/pdf"),
            "invalid_resume_content",
        ),
        (
            SimpleUploadedFile("resume.pdf", b"%PDF-1.7", content_type="application/msword"),
            "invalid_resume_mime",
        ),
        (
            zip_upload("resume.docx", {"payload.txt": "not a Word document"}),
            "invalid_resume_content",
        ),
        (
            zip_upload(
                "resume.docx",
                {"[Content_Types].xml": "<Types />", "word/metadata.xml": "<metadata />"},
            ),
            "invalid_resume_content",
        ),
    ],
)
def test_invalid_resume_extension_mime_or_content_is_rejected(
    api_client, candidate, job, private_storage, uploaded, error_code
):
    response = auth(api_client, candidate).post(
        reverse("application-list"),
        {"job": job.id, "resume": uploaded},
        format="multipart",
    )

    assert response.status_code == 400
    assert response.data["resume"][0].code == error_code
    assert not Application.objects.exists()


@pytest.mark.django_db
def test_oversized_resume_is_rejected(api_client, candidate, job, private_storage):
    uploaded = SimpleUploadedFile(
        "resume.pdf", b"%PDF-" + b"x" * (MAX_RESUME_SIZE - 4), content_type="application/pdf"
    )
    response = auth(api_client, candidate).post(
        reverse("application-list"), {"job": job.id, "resume": uploaded}, format="multipart"
    )

    assert response.status_code == 400
    assert response.data["resume"][0].code == "resume_too_large"


@pytest.mark.django_db
def test_original_filename_is_sanitized_for_download(api_client, candidate, job, private_storage):
    response = auth(api_client, candidate).post(
        reverse("application-list"),
        {"job": job.id, "resume": resume_file("pdf", "..\\private\\My Resume.PDF")},
        format="multipart",
    )
    application = Application.objects.get()

    assert response.status_code == 201
    assert application.resume_original_name == "My Resume.PDF"
    download = api_client.get(reverse("application-resume", args=[application.id]))
    assert download.status_code == 200
    assert "My Resume.PDF" in download["Content-Disposition"]
    assert "private" not in download["Content-Disposition"]
    assert download["Cache-Control"] == "private, no-store"
    assert download["X-Content-Type-Options"] == "nosniff"
    assert b"".join(download.streaming_content).startswith(b"%PDF-")


@pytest.mark.django_db
def test_resume_download_is_owner_scoped_and_survives_soft_delete(
    api_client, candidate, employer, employer2, job, private_storage
):
    application = Application.objects.create(
        candidate=candidate,
        job=job,
        resume=resume_file(),
        resume_original_name="resume.pdf",
    )
    url = reverse("application-resume", args=[application.id])
    other_candidate = User.objects.create_user(
        "other-candidate@example.com", "StrongPass123!", role=User.Role.CANDIDATE
    )

    assert APIClient().get(url).status_code == 401
    assert auth(APIClient(), other_candidate).get(url).status_code == 404
    assert auth(APIClient(), employer2).get(url).status_code == 404
    candidate_response = auth(APIClient(), candidate).get(url)
    assert candidate_response.status_code == 200
    candidate_response.close()

    job.soft_delete()
    employer_response = auth(APIClient(), employer).get(url)
    assert employer_response.status_code == 200
    employer_response.close()


@pytest.mark.django_db
def test_missing_resume_is_404_and_staff_session_can_download(
    candidate, employer, job, private_storage
):
    without_resume = Application.objects.create(candidate=candidate, job=job)
    assert (
        auth(APIClient(), candidate)
        .get(reverse("application-resume", args=[without_resume.id]))
        .status_code
        == 404
    )

    without_resume.resume = resume_file()
    without_resume.resume_original_name = "resume.pdf"
    without_resume.save(update_fields=["resume", "resume_original_name", "updated_at"])
    staff = User.objects.create_superuser(
        "staff@example.com", "StrongPass123!", role=User.Role.EMPLOYER
    )
    client = APIClient()
    client.force_login(staff)
    response = client.get(reverse("application-resume", args=[without_resume.id]))
    assert response.status_code == 200
    response.close()


@pytest.mark.django_db
def test_stored_resume_is_cleaned_up_if_answer_creation_fails(
    api_client, candidate, job, private_storage, monkeypatch
):
    from jobs.models import ApplicationQuestion

    question = ApplicationQuestion.objects.create(
        job=job, text="Required", question_type="BOOLEAN", required=True
    )
    existing_files = stored_files(private_storage)

    def fail_bulk_create(*args, **kwargs):
        raise RuntimeError("simulated answer persistence failure")

    monkeypatch.setattr(ApplicationAnswer.objects, "bulk_create", fail_bulk_create)
    with pytest.raises(RuntimeError, match="simulated"):
        auth(api_client, candidate).post(
            reverse("application-list"),
            {
                "job": job.id,
                "resume": resume_file(),
                "answers": json.dumps([{"question": question.id, "value": True}]),
            },
            format="multipart",
        )

    assert not Application.objects.exists()
    assert stored_files(private_storage) == existing_files
