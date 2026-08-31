import django_filters

from jobs.models import Job, Skill


class JobFilter(django_filters.FilterSet):
    location = django_filters.CharFilter(field_name="location", lookup_expr="iexact")
    skills = django_filters.ModelMultipleChoiceFilter(
        field_name="skills", queryset=Skill.objects.all(), distinct=True
    )

    class Meta:
        model = Job
        fields = ("location", "skills", "employment_type", "is_active")
