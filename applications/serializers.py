from rest_framework import serializers

from applications.models import Application
from jobs.models import Job


class ApplicationSerializer(serializers.ModelSerializer):
    candidate = serializers.CharField(source="candidate.email", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    job = serializers.PrimaryKeyRelatedField(queryset=Job.all_objects.all())

    class Meta:
        model = Application
        fields = (
            "id",
            "job",
            "job_title",
            "candidate",
            "status",
            "cover_letter",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "job_title",
            "candidate",
            "status",
            "created_at",
            "updated_at",
        )

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


class ApplicationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ("status",)
