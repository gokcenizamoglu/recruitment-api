from rest_framework import serializers

from jobs.models import Job, Skill


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
