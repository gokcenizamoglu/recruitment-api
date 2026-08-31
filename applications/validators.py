import re
import uuid
import zipfile
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.utils import timezone

MAX_RESUME_SIZE = 5 * 1024 * 1024
MAX_ORIGINAL_NAME_LENGTH = 200

ALLOWED_RESUME_TYPES = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword", "application/x-ole-storage"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
}

OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")


def sanitize_original_filename(filename):
    basename = PurePosixPath(str(filename).replace("\\", "/")).name
    basename = re.sub(r"[\x00-\x1f\x7f]", "", basename).strip()
    if not basename:
        basename = "resume"

    suffix = PurePosixPath(basename).suffix.lower()
    if len(basename) > MAX_ORIGINAL_NAME_LENGTH:
        stem_limit = MAX_ORIGINAL_NAME_LENGTH - len(suffix)
        basename = f"{basename[:stem_limit]}{suffix}"
    return basename


def resume_upload_to(_instance, filename):
    suffix = PurePosixPath(sanitize_original_filename(filename)).suffix.lower()
    now = timezone.now()
    return f"resumes/{now:%Y/%m}/{uuid.uuid4().hex}{suffix}"


def validate_resume_file(uploaded_file):
    if uploaded_file.size > MAX_RESUME_SIZE:
        raise ValidationError("Resume must not exceed 5 MiB.", code="resume_too_large")

    original_name = sanitize_original_filename(uploaded_file.name)
    suffix = PurePosixPath(original_name).suffix.lower()
    if suffix not in ALLOWED_RESUME_TYPES:
        raise ValidationError(
            "Resume must be a PDF, DOC, or DOCX file.", code="invalid_resume_extension"
        )

    content_type = getattr(uploaded_file, "content_type", "")
    if content_type and content_type.lower() not in ALLOWED_RESUME_TYPES[suffix]:
        raise ValidationError(
            "Resume content type does not match its extension.", code="invalid_resume_mime"
        )

    original_position = uploaded_file.tell()
    try:
        uploaded_file.seek(0)
        signature = uploaded_file.read(8)
        if suffix == ".pdf" and not signature.startswith(b"%PDF-"):
            raise ValidationError("Invalid PDF file content.", code="invalid_resume_content")
        if suffix == ".doc" and signature != OLE_SIGNATURE:
            raise ValidationError("Invalid DOC file content.", code="invalid_resume_content")
        if suffix == ".docx":
            uploaded_file.seek(0)
            try:
                with zipfile.ZipFile(uploaded_file) as archive:
                    names = archive.namelist()
                    is_word_document = (
                        "[Content_Types].xml" in names and "word/document.xml" in names
                    )
            except (OSError, zipfile.BadZipFile):
                is_word_document = False
            if not is_word_document:
                raise ValidationError("Invalid DOCX file content.", code="invalid_resume_content")
    finally:
        uploaded_file.seek(original_position)
