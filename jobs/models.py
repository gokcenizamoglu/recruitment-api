import re

from django.conf import settings
from django.db import models
from django.utils import timezone


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = re.sub(r"\s+", " ", self.name.strip()).lower()
        super().save(*args, **kwargs)


class ActiveJobManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Job(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full time"
        PART_TIME = "PART_TIME", "Part time"
        CONTRACT = "CONTRACT", "Contract"
        INTERNSHIP = "INTERNSHIP", "Internship"

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="jobs",
        limit_choices_to={"role": "EMPLOYER"},
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    skills = models.ManyToManyField(Skill, related_name="jobs")
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = ActiveJobManager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["employer", "deleted_at"]),
            models.Index(fields=["is_active", "deleted_at"]),
        ]

    def __str__(self):
        return self.title

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])
