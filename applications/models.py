from django.conf import settings
from django.db import models

from jobs.models import Job


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
