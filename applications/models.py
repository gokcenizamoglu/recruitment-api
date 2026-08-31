from django.conf import settings
from django.db import models

from applications.validators import resume_upload_to
from jobs.models import ApplicationQuestion, Job


class Application(models.Model):
    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        REJECTED = "REJECTED", "Rejected"
        HIRED = "HIRED", "Hired"

    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="applications")
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="applications",
        limit_choices_to={"role": "CANDIDATE"},
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.APPLIED)
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to=resume_upload_to, blank=True)
    resume_original_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=("job", "candidate"), name="unique_application_per_job_candidate"
            )
        ]
        indexes = [models.Index(fields=["candidate", "created_at"])]

    def __str__(self):
        return f"{self.candidate} -> {self.job}"


class ApplicationAnswer(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(
        ApplicationQuestion, on_delete=models.PROTECT, related_name="answers"
    )
    question_text_snapshot = models.CharField(max_length=500)
    question_type_snapshot = models.CharField(max_length=20)
    options_snapshot = models.JSONField(default=list, blank=True)
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=("application", "question"),
                name="unique_answer_per_application_question",
            )
        ]

    def __str__(self):
        return f"Answer {self.id} for application {self.application_id}"
