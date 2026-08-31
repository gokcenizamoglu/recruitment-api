from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Skill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField()),
                ("location", models.CharField(max_length=200)),
                ("employment_type", models.CharField(choices=[("FULL_TIME", "Full time"), ("PART_TIME", "Part time"), ("CONTRACT", "Contract"), ("INTERNSHIP", "Internship")], max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("deleted_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employer", models.ForeignKey(limit_choices_to={"role": "EMPLOYER"}, on_delete=django.db.models.deletion.PROTECT, related_name="jobs", to=settings.AUTH_USER_MODEL)),
                ("skills", models.ManyToManyField(related_name="jobs", to="jobs.skill")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [models.Index(fields=["employer", "deleted_at"], name="jobs_job_employer_45e924_idx"), models.Index(fields=["is_active", "deleted_at"], name="jobs_job_is_acti_50f26b_idx")],
            },
        ),
    ]
