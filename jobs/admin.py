from django.contrib import admin
from django.db.models import Count
from unfold.admin import ModelAdmin

from jobs.models import Job, Skill


class DeletedStateFilter(admin.SimpleListFilter):
    title = "deleted state"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (("yes", "Soft-deleted"), ("no", "Not deleted"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(deleted_at__isnull=False)
        if self.value() == "no":
            return queryset.filter(deleted_at__isnull=True)
        return queryset


@admin.register(Job)
class JobAdmin(ModelAdmin):
    list_display = (
        "title",
        "employer",
        "location",
        "employment_type",
        "active_status",
        "deleted_status",
        "application_count",
        "created_at",
    )
    list_filter = (
        "is_active",
        "employment_type",
        DeletedStateFilter,
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = ("title", "description", "location", "employer__email")
    autocomplete_fields = ("employer", "skills")
    readonly_fields = ("deleted_at", "created_at", "updated_at")
    ordering = ("-created_at", "-id")
    actions = ("restore_selected",)

    def get_queryset(self, request):
        return (
            Job.all_objects.select_related("employer")
            .prefetch_related("skills")
            .annotate(_application_count=Count("applications"))
        )

    @admin.display(boolean=True, description="Active")
    def active_status(self, obj):
        return obj.is_active

    @admin.display(boolean=True, description="Deleted")
    def deleted_status(self, obj):
        return obj.deleted_at is not None

    @admin.display(description="Applications", ordering="_application_count")
    def application_count(self, obj):
        return obj._application_count

    @admin.action(description="Restore selected jobs")
    def restore_selected(self, request, queryset):
        restored = queryset.filter(deleted_at__isnull=False).update(deleted_at=None, is_active=True)
        self.message_user(request, f"{restored} job(s) restored.")


@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ("name", "job_count")
    search_fields = ("name",)
    ordering = ("name", "id")

    def get_queryset(self, request):
        return Skill.objects.annotate(_job_count=Count("jobs"))

    @admin.display(description="Jobs", ordering="_job_count")
    def job_count(self, obj):
        return obj._job_count
