from django.contrib import admin
from unfold.admin import ModelAdmin

from applications.models import Application


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = ("candidate", "job", "employer", "status", "created_at", "updated_at")
    list_filter = ("status", ("created_at", admin.DateFieldListFilter), "job")
    search_fields = (
        "candidate__email",
        "candidate__first_name",
        "candidate__last_name",
        "job__title",
        "job__employer__email",
    )
    list_select_related = ("candidate", "job", "job__employer")
    readonly_fields = ("candidate", "job", "created_at", "updated_at")
    ordering = ("-created_at", "-id")

    @admin.display(description="Employer")
    def employer(self, obj):
        return obj.job.employer

    def has_delete_permission(self, request, obj=None):
        return False
