from django.db import IntegrityError, transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.models import User
from applications.models import Application
from applications.serializers import ApplicationSerializer, ApplicationStatusSerializer
from jobs.permissions import IsCandidate, IsEmployer


class ApplicationViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ApplicationSerializer
    queryset = Application.objects.none()

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.queryset
        queryset = Application.objects.select_related("job", "candidate", "job__employer")
        if self.request.user.role == User.Role.CANDIDATE:
            return queryset.filter(candidate=self.request.user)
        return queryset.filter(job__employer=self.request.user, job__deleted_at__isnull=True)

    def get_permissions(self):
        if self.action == "create":
            return [IsCandidate()]
        if self.action == "status":
            return [IsEmployer()]
        return super().get_permissions()

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save(candidate=self.request.user)
        except IntegrityError as exc:
            raise ValidationError(
                {"job": ["You have already applied to this job."]},
                code="duplicate_application",
            ) from exc

    @action(detail=True, methods=["patch"], url_path="status")
    def status(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationStatusSerializer(
            application, data=request.data, partial=True, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ApplicationSerializer(application).data)
