from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("jobs", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("APPLIED", "Applied"), ("SHORTLISTED", "Shortlisted"), ("REJECTED", "Rejected"), ("HIRED", "Hired")], default="APPLIED", max_length=16)),
                ("cover_letter", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("candidate", models.ForeignKey(limit_choices_to={"role": "CANDIDATE"}, on_delete=django.db.models.deletion.PROTECT, related_name="applications", to=settings.AUTH_USER_MODEL)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="applications", to="jobs.job")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [models.Index(fields=["candidate", "created_at"], name="applicatio_candida_819df1_idx")],
                "constraints": [models.UniqueConstraint(fields=("job", "candidate"), name="unique_application_per_job_candidate")],
            },
        )
    ]
