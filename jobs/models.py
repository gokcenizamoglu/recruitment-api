import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
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


class ApplicationQuestion(models.Model):
    MAX_OPTIONS = 20
    MAX_OPTION_LENGTH = 200

    class QuestionType(models.TextChoices):
        TEXT = "TEXT", "Text"
        TEXTAREA = "TEXTAREA", "Textarea"
        NUMBER = "NUMBER", "Number"
        BOOLEAN = "BOOLEAN", "Boolean"
        SINGLE_CHOICE = "SINGLE_CHOICE", "Single choice"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="application_questions")
    text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QuestionType.choices)
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    options = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["job", "is_active", "order"])]
        constraints = [
            models.CheckConstraint(condition=Q(order__gte=0), name="question_order_non_negative")
        ]

    def __str__(self):
        return self.text

    def clean(self):
        super().clean()
        self.text = self.text.strip()
        if not self.text:
            raise ValidationError({"text": "Question text cannot be blank."})

        if self.pk:
            original_type = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("question_type", flat=True)
                .first()
            )
            if original_type != self.question_type and self.answers.exists():
                raise ValidationError(
                    {"question_type": "Question type cannot change after answers are submitted."}
                )

        if self.question_type != self.QuestionType.SINGLE_CHOICE:
            if self.options:
                raise ValidationError({"options": "Options are allowed only for single choice."})
            self.options = []
            return

        if not isinstance(self.options, list):
            raise ValidationError({"options": "Options must be a list."})
        if not 2 <= len(self.options) <= self.MAX_OPTIONS:
            raise ValidationError(
                {"options": f"Single choice questions require 2-{self.MAX_OPTIONS} options."}
            )

        normalized = []
        for option in self.options:
            if not isinstance(option, str):
                raise ValidationError({"options": "Each option must be a string."})
            option = option.strip()
            if not option:
                raise ValidationError({"options": "Options cannot be blank."})
            if len(option) > self.MAX_OPTION_LENGTH:
                raise ValidationError(
                    {"options": f"Options cannot exceed {self.MAX_OPTION_LENGTH} characters."}
                )
            normalized.append(option)
        if len(normalized) != len(set(normalized)):
            raise ValidationError({"options": "Options must be unique."})
        self.options = normalized
