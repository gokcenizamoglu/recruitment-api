from pathlib import PurePosixPath

from django.db import IntegrityError
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import User
from applications.models import Application
from applications.serializers import (
    ApplicationCreateSerializer,
    ApplicationMultipartSerializer,
    ApplicationReadSerializer,
    ApplicationStatusSerializer,
)
from applications.validators import sanitize_original_filename
from jobs.permissions import IsCandidate, IsEmployer

RESUME_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class ApplicationViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ApplicationReadSerializer
    queryset = Application.objects.none()

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationCreateSerializer
        if self.action == "status":
            return ApplicationStatusSerializer
        return ApplicationReadSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.queryset
        queryset = Application.objects.select_related(
            "job", "candidate", "job__employer"
        ).prefetch_related("answers")
        if self.request.user.role == User.Role.CANDIDATE:
            return queryset.filter(candidate=self.request.user)
        return queryset.filter(job__employer=self.request.user, job__deleted_at__isnull=True)

    def get_permissions(self):
        if self.action == "create":
            return [IsCandidate()]
        if self.action == "status":
            return [IsEmployer()]
        return super().get_permissions()

    @extend_schema(
        request={
            "application/json": ApplicationCreateSerializer,
            "multipart/form-data": ApplicationMultipartSerializer,
        },
        responses={201: ApplicationReadSerializer},
        examples=[
            OpenApiExample(
                "Multipart answers JSON string",
                value={
                    "job": 42,
                    "cover_letter": "I would like to apply.",
                    "answers": '[{"question": 3, "value": 5}, {"question": 4, "value": true}]',
                },
                request_only=True,
            )
        ],
        description=(
            "Create an application atomically. JSON requests may send answers as an array. "
            "For multipart/form-data, send answers as a JSON-encoded array string and resume "
            "as a PDF, DOC, or DOCX file up to 5 MiB."
        ),
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = serializer.save()
        except IntegrityError as exc:
            raise ValidationError(
                {"job": ["You have already applied to this job."]},
                code="duplicate_application",
            ) from exc
        output = ApplicationReadSerializer(application, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="status")
    def status(self, request, pk=None):
        application = self.get_object()
        serializer = self.get_serializer(application, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ApplicationReadSerializer(application, context=self.get_serializer_context()).data
        )

    @extend_schema(
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
        description=(
            "Download a submitted resume. Available only to the candidate, the owning employer, "
            "or staff. Unrelated authenticated users receive 404."
        ),
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="resume",
        authentication_classes=[JWTAuthentication, SessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def resume(self, request, pk=None):
        queryset = Application.objects.select_related("candidate", "job__employer")
        if request.user.is_staff:
            application = get_object_or_404(queryset, pk=pk)
        elif request.user.role == User.Role.CANDIDATE:
            application = get_object_or_404(queryset, pk=pk, candidate=request.user)
        elif request.user.role == User.Role.EMPLOYER:
            application = get_object_or_404(queryset, pk=pk, job__employer=request.user)
        else:
            raise NotFound()

        if not application.resume:
            raise NotFound()

        suffix = PurePosixPath(application.resume.name).suffix.lower()
        filename = sanitize_original_filename(application.resume_original_name or f"resume{suffix}")
        response = FileResponse(
            application.resume.open("rb"),
            as_attachment=True,
            filename=filename,
            content_type=RESUME_CONTENT_TYPES.get(suffix, "application/octet-stream"),
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
