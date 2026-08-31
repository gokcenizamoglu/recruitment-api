from django.core.management.base import BaseCommand

from accounts.models import User
from jobs.models import Job, Skill


class Command(BaseCommand):
    help = "Create a small, repeatable demo dataset."

    def handle(self, *args, **options):
        employer, _ = User.objects.get_or_create(
            email="employer@example.com",
            defaults={"role": User.Role.EMPLOYER, "first_name": "Demo", "last_name": "Employer"},
        )
        employer.set_password("DemoPassword123!")
        employer.save(update_fields=["password"])
        candidate, _ = User.objects.get_or_create(
            email="candidate@example.com",
            defaults={"role": User.Role.CANDIDATE, "first_name": "Demo", "last_name": "Candidate"},
        )
        candidate.set_password("DemoPassword123!")
        candidate.save(update_fields=["password"])

        skill_names = ("python", "django", "sql", "docker")
        skills = {name: Skill.objects.get_or_create(name=name)[0] for name in skill_names}
        job_specs = [
            ("Senior Django Engineer", "Remote", "FULL_TIME", ("python", "django", "sql")),
            ("Platform Intern", "Istanbul", "INTERNSHIP", ("python", "docker")),
            ("API Contractor", "Remote", "CONTRACT", ("python", "sql")),
        ]
        for title, location, employment_type, skill_names in job_specs:
            job, _ = Job.all_objects.get_or_create(
                employer=employer,
                title=title,
                defaults={
                    "description": f"Demo opportunity: {title}",
                    "location": location,
                    "employment_type": employment_type,
                },
            )
            job.skills.set([skills[name] for name in skill_names])
        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
