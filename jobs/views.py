from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.serializers import ApplicationSerializer
from jobs.filters import JobFilter
from jobs.models import Job, Skill
from jobs.permissions import IsEmployer, IsEmployerOrReadOnly, IsJobOwnerOrReadOnly
from jobs.serializers import JobSerializer, SkillSerializer


class SkillViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsEmployer()]
        return [IsAuthenticated()]


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    filterset_class = JobFilter
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "updated_at", "title")
    ordering = ("-created_at", "-id")
    lookup_value_regex = r"\d+"
    permission_classes = [IsEmployerOrReadOnly, IsJobOwnerOrReadOnly]

    def get_queryset(self):
        queryset = Job.objects.select_related("employer").prefetch_related("skills")
        if self.action in {"update", "partial_update", "destroy"}:
            return queryset.filter(employer=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(employer=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(responses=ApplicationSerializer(many=True))
    @action(detail=True, methods=["get"], permission_classes=[IsEmployer])
    def applications(self, request, pk=None):
        job = self.get_object()
        if job.employer_id != request.user.id:
            return Response(status=status.HTTP_404_NOT_FOUND)
        queryset = job.applications.select_related("candidate", "job").all()
        page = self.paginate_queryset(queryset)
        serializer = ApplicationSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
