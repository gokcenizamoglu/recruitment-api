import json
import math

from django.db import transaction
from django.urls import reverse
from rest_framework import serializers

from applications.models import Application, ApplicationAnswer
from applications.validators import sanitize_original_filename, validate_resume_file
from jobs.models import ApplicationQuestion, Job

MAX_TEXT_ANSWER_LENGTH = 500
MAX_TEXTAREA_ANSWER_LENGTH = 5000


class ApplicationAnswerInputSerializer(serializers.Serializer):
    question = serializers.IntegerField(min_value=1)
    value = serializers.JSONField()


class AnswersField(serializers.ListField):
    child = ApplicationAnswerInputSerializer()

    def get_value(self, dictionary):
        if hasattr(dictionary, "getlist") and self.field_name in dictionary:
            return dictionary.get(self.field_name)
        return super().get_value(dictionary)

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError("Answers must be a valid JSON array.") from exc
        return super().to_internal_value(data)


class ApplicationAnswerReadSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question_text_snapshot", read_only=True)
    question_type = serializers.CharField(source="question_type_snapshot", read_only=True)
    options = serializers.JSONField(source="options_snapshot", read_only=True)

    class Meta:
        model = ApplicationAnswer
        fields = ("question", "question_text", "question_type", "options", "value")
        read_only_fields = fields


class ApplicationReadSerializer(serializers.ModelSerializer):
    candidate = serializers.CharField(source="candidate.email", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    resume_available = serializers.SerializerMethodField()
    resume_download_url = serializers.SerializerMethodField()
    answers = ApplicationAnswerReadSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "job",
            "job_title",
            "candidate",
            "status",
            "cover_letter",
            "resume_available",
            "resume_download_url",
            "answers",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_resume_available(self, obj) -> bool:
        return bool(obj.resume)

    def get_resume_download_url(self, obj) -> str | None:
        if not obj.resume:
            return None
        return reverse("application-resume", args=[obj.pk])


class ApplicationCreateSerializer(serializers.ModelSerializer):
    resume = serializers.FileField(
        required=False, allow_empty_file=False, validators=[validate_resume_file], write_only=True
    )
    answers = AnswersField(required=False, default=list, write_only=True)
    job = serializers.PrimaryKeyRelatedField(queryset=Job.all_objects.all())

    class Meta:
        model = Application
        fields = ("job", "cover_letter", "resume", "answers")

    def validate_job(self, job):
        if job.deleted_at is not None or not job.is_active:
            raise serializers.ValidationError(
                "This job is not accepting applications.", code="inactive_job"
            )
        request = self.context["request"]
        if Application.objects.filter(job=job, candidate=request.user).exists():
            raise serializers.ValidationError(
                "You have already applied to this job.", code="duplicate_application"
            )
        return job

    def validate(self, attrs):
        attrs = super().validate(attrs)
        job = attrs["job"]
        submitted = attrs.get("answers", [])
        submitted_ids = [item["question"] for item in submitted]

        duplicate_ids = sorted(
            question_id
            for question_id in set(submitted_ids)
            if submitted_ids.count(question_id) > 1
        )
        if duplicate_ids:
            raise serializers.ValidationError(
                {"answers": f"Duplicate answers were submitted for questions: {duplicate_ids}."}
            )

        questions = {
            question.id: question
            for question in ApplicationQuestion.objects.filter(pk__in=submitted_ids)
        }
        validated_answers = []
        answer_errors = {}
        for index, item in enumerate(submitted):
            question_id = item["question"]
            question = questions.get(question_id)
            if question is None or question.job_id != job.id:
                answer_errors[index] = "Question does not belong to the selected job."
                continue
            if not question.is_active:
                answer_errors[index] = "Inactive questions cannot be answered."
                continue
            try:
                value = self._validate_answer_value(question, item["value"])
            except serializers.ValidationError as exc:
                answer_errors[index] = exc.detail
                continue
            validated_answers.append({"question": question, "value": value})

        if answer_errors:
            raise serializers.ValidationError({"answers": answer_errors})

        answered_ids = {item["question"].id for item in validated_answers}
        missing_required = list(
            ApplicationQuestion.objects.filter(job=job, is_active=True, required=True)
            .exclude(id__in=answered_ids)
            .values_list("id", flat=True)
        )
        if missing_required:
            raise serializers.ValidationError(
                {"answers": f"Required questions are missing: {missing_required}."}
            )

        attrs["answers"] = validated_answers
        return attrs

    @staticmethod
    def _validate_answer_value(question, value):
        question_type = question.question_type
        if question_type in {
            ApplicationQuestion.QuestionType.TEXT,
            ApplicationQuestion.QuestionType.TEXTAREA,
        }:
            if not isinstance(value, str):
                raise serializers.ValidationError("Answer must be a string.")
            value = value.strip()
            if question.required and not value:
                raise serializers.ValidationError("Required text answers cannot be blank.")
            maximum = (
                MAX_TEXT_ANSWER_LENGTH
                if question_type == ApplicationQuestion.QuestionType.TEXT
                else MAX_TEXTAREA_ANSWER_LENGTH
            )
            if len(value) > maximum:
                raise serializers.ValidationError(f"Answer cannot exceed {maximum} characters.")
            return value

        if question_type == ApplicationQuestion.QuestionType.NUMBER:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise serializers.ValidationError("Answer must be a JSON number.")
            if not math.isfinite(value):
                raise serializers.ValidationError("Answer must be a finite number.")
            return value

        if question_type == ApplicationQuestion.QuestionType.BOOLEAN:
            if type(value) is not bool:
                raise serializers.ValidationError("Answer must be a JSON boolean.")
            return value

        if question_type == ApplicationQuestion.QuestionType.SINGLE_CHOICE:
            if not isinstance(value, str) or value not in question.options:
                raise serializers.ValidationError("Answer must match one configured option.")
            return value

        raise serializers.ValidationError("Unsupported question type.")

    def create(self, validated_data):
        answers = validated_data.pop("answers", [])
        resume = validated_data.get("resume")
        if resume:
            validated_data["resume_original_name"] = sanitize_original_filename(resume.name)

        application = None
        try:
            with transaction.atomic():
                application = Application(candidate=self.context["request"].user, **validated_data)
                application.save(force_insert=True)
                ApplicationAnswer.objects.bulk_create(
                    [
                        ApplicationAnswer(
                            application=application,
                            question=item["question"],
                            question_text_snapshot=item["question"].text,
                            question_type_snapshot=item["question"].question_type,
                            options_snapshot=list(item["question"].options),
                            value=item["value"],
                        )
                        for item in answers
                    ]
                )
        except Exception:
            if application and application.resume and application.resume.name:
                application.resume.storage.delete(application.resume.name)
            raise
        return application


class ApplicationMultipartSerializer(serializers.Serializer):
    job = serializers.IntegerField(min_value=1)
    cover_letter = serializers.CharField(required=False, allow_blank=True)
    resume = serializers.FileField(required=False)
    answers = serializers.CharField(
        required=False,
        help_text=(
            "JSON-encoded answer array, for example: "
            '[{"question": 3, "value": 5}, {"question": 4, "value": true}]'
        ),
    )


class ApplicationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ("status",)


# Backward-compatible import name for internal callers and schema consumers.
ApplicationSerializer = ApplicationReadSerializer
