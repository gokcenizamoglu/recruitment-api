from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from applications.models import Application, ApplicationAnswer


class ApplicationAnswerInline(admin.TabularInline):
    model = ApplicationAnswer
    fields = (
        "question",
        "question_text_snapshot",
        "question_type_snapshot",
        "options_snapshot",
        "value",
        "created_at",
    )
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = (
        "candidate",
        "job",
        "employer",
        "status",
        "resume_present",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", ("created_at", admin.DateFieldListFilter), "job")
    search_fields = (
        "candidate__email",
        "candidate__first_name",
        "candidate__last_name",
        "job__title",
        "job__employer__email",
    )
    list_select_related = ("candidate", "job", "job__employer")
    readonly_fields = (
        "candidate",
        "job",
        "resume_download",
        "created_at",
        "updated_at",
    )
    exclude = ("resume", "resume_original_name")
    inlines = (ApplicationAnswerInline,)
    ordering = ("-created_at", "-id")

    @admin.display(description="Employer")
    def employer(self, obj):
        return obj.job.employer

    @admin.display(boolean=True, description="Resume")
    def resume_present(self, obj):
        return bool(obj.resume)

    @admin.display(description="Resume")
    def resume_download(self, obj):
        if not obj or not obj.resume:
            return "No resume submitted"
        url = reverse("application-resume", args=[obj.pk])
        return format_html('<a href="{}">Download protected resume</a>', url)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ApplicationAnswer)
class ApplicationAnswerAdmin(ModelAdmin):
    list_display = (
        "application",
        "question_text_snapshot",
        "question_type_snapshot",
        "created_at",
    )
    list_filter = ("question_type_snapshot", ("created_at", admin.DateFieldListFilter))
    search_fields = (
        "question_text_snapshot",
        "application__candidate__email",
        "application__job__title",
    )
    list_select_related = ("application", "application__candidate", "application__job")
    readonly_fields = (
        "application",
        "question",
        "question_text_snapshot",
        "question_type_snapshot",
        "options_snapshot",
        "value",
        "created_at",
    )
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
