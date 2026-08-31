from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from jobs.models import ApplicationQuestion, Job, Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "name")
        read_only_fields = ("id",)

    def validate_name(self, value):
        normalized = " ".join(value.split()).lower()
        if not normalized:
            raise serializers.ValidationError("Skill name cannot be empty.")
        return normalized


class JobSerializer(serializers.ModelSerializer):
    employer = serializers.CharField(source="employer.email", read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        source="skills", many=True, queryset=Skill.objects.all(), write_only=True
    )

    class Meta:
        model = Job
        fields = (
            "id",
            "employer",
            "title",
            "description",
            "location",
            "employment_type",
            "skills",
            "skill_ids",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "employer", "created_at", "updated_at")


class ApplicationQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationQuestion
        fields = (
            "id",
            "text",
            "question_type",
            "required",
            "order",
            "is_active",
            "options",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        question = self.instance or ApplicationQuestion()
        current_type = question.question_type
        for field in ("text", "question_type", "required", "order", "is_active", "options"):
            if field in attrs:
                setattr(question, field, attrs[field])

        if (
            self.instance
            and "question_type" in attrs
            and attrs["question_type"] != current_type
            and self.instance.answers.exists()
        ):
            raise serializers.ValidationError(
                {"question_type": "Question type cannot change after answers are submitted."}
            )

        try:
            question.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        attrs["text"] = question.text
        attrs["options"] = question.options
        return attrs
