from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from jobs.models import ApplicationQuestion, Job
from jobs.serializers import ApplicationQuestionSerializer


class QuestionAccessMixin:
    permission_classes = [IsAuthenticated]

    def get_job(self):
        if not hasattr(self, "_job"):
            self._job = get_object_or_404(
                Job.objects.select_related("employer"), pk=self.kwargs["job_id"]
            )
        return self._job

    def is_owner(self):
        job = self.get_job()
        return (
            self.request.user.role == User.Role.EMPLOYER and job.employer_id == self.request.user.id
        )

    def enforce_owner(self):
        if self.request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied("Only employers may manage application questions.")
        if not self.is_owner():
            raise NotFound()


class ApplicationQuestionListCreateView(QuestionAccessMixin, generics.ListCreateAPIView):
    serializer_class = ApplicationQuestionSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ApplicationQuestion.objects.none()
        queryset = ApplicationQuestion.objects.filter(job=self.get_job())
        if not self.is_owner():
            queryset = queryset.filter(is_active=True)
        return queryset

    def create(self, request, *args, **kwargs):
        self.enforce_owner()
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(job=self.get_job())


class ApplicationQuestionDetailView(QuestionAccessMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ApplicationQuestionSerializer
    lookup_url_kwarg = "question_id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ApplicationQuestion.objects.none()
        queryset = ApplicationQuestion.objects.filter(job=self.get_job())
        if self.request.method == "GET" and not self.is_owner():
            queryset = queryset.filter(is_active=True)
        return queryset

    def update(self, request, *args, **kwargs):
        self.enforce_owner()
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self.enforce_owner()
        question = self.get_object()
        if question.is_active:
            question.is_active = False
            question.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
