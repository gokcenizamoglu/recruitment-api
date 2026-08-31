from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from applications.models import Application
from jobs.models import Job, Skill

DEMO_PASSWORD = "DemoPass123!"
EMPLOYERS = {
    "employer.istanbul@example.com": ("Aylin", "Demir"),
    "employer.eu@example.com": ("Jonas", "Weber"),
    "employer.global@example.com": ("Maya", "Okafor"),
}
CANDIDATES = {
    "candidate1@example.com": ("Elif", "Kaya"),
    "candidate2@example.com": ("Liam", "Murphy"),
    "candidate3@example.com": ("Sofia", "Rossi"),
    "candidate4@example.com": ("Noah", "Schmidt"),
    "candidate5@example.com": ("Amara", "Mensah"),
    "candidate6@example.com": ("Kenji", "Sato"),
    "candidate7@example.com": ("Nora", "Dubois"),
    "candidate8@example.com": ("Daniel", "Cohen"),
}
SKILL_NAMES = (
    "Python",
    "Django",
    "Django REST Framework",
    "PostgreSQL",
    "Docker",
    "Redis",
    "AWS",
    "Azure",
    "Git",
    "CI/CD",
    "Linux",
    "REST APIs",
    "SQL",
    "JavaScript",
    "TypeScript",
    "React",
    "Next.js",
    "Node.js",
    "FastAPI",
    "Kubernetes",
    "Terraform",
    "RabbitMQ",
    "Celery",
    "Elasticsearch",
    "System Design",
    "Microservices",
    "API Integration",
)

JOB_SPECS = (
    (
        "Senior Django Developer",
        "employer.istanbul@example.com",
        "Istanbul, Türkiye",
        "FULL_TIME",
        True,
        False,
        "Lead backend delivery for a product team building reliable Python services. You will shape APIs, review designs, and coach engineers while partnering with product and QA.",
        ("Python", "Django", "Django REST Framework", "PostgreSQL", "Docker"),
    ),
    (
        "Airport IT Systems Engineer",
        "employer.istanbul@example.com",
        "Istanbul, Türkiye",
        "FULL_TIME",
        True,
        False,
        "Design integrations for passenger and airport operations systems. The role combines API engineering, incident ownership, and careful collaboration with infrastructure teams.",
        ("Python", "API Integration", "REST APIs", "PostgreSQL", "Linux"),
    ),
    (
        "Backend Engineer",
        "employer.istanbul@example.com",
        "Hybrid - Istanbul",
        "FULL_TIME",
        True,
        False,
        "Build maintainable services for a growing marketplace platform. Expect hands-on work across REST APIs, data modeling, observability, and pragmatic delivery practices.",
        ("Python", "FastAPI", "PostgreSQL", "Docker", "Git"),
    ),
    (
        "QA Automation Engineer",
        "employer.istanbul@example.com",
        "Ankara, Türkiye",
        "FULL_TIME",
        True,
        False,
        "Create dependable automated coverage for web and API workflows. You will work with developers to improve release confidence and turn production lessons into tests.",
        ("Python", "REST APIs", "SQL", "Docker", "CI/CD"),
    ),
    (
        "Technical Lead",
        "employer.istanbul@example.com",
        "Remote - Worldwide",
        "FULL_TIME",
        True,
        False,
        "Guide a distributed engineering team through architecture decisions and incremental modernization. Strong communication and a systems-thinking mindset are essential.",
        ("System Design", "Python", "Microservices", "AWS", "Kubernetes"),
    ),
    (
        "Senior Backend Engineer",
        "employer.eu@example.com",
        "Berlin, Germany",
        "FULL_TIME",
        True,
        False,
        "Own core services for a European technology company with a focus on performance and resilience. You will improve service boundaries, data access, and operational tooling.",
        ("Python", "Django", "PostgreSQL", "Redis", "Kubernetes"),
    ),
    (
        "Platform Engineer",
        "employer.eu@example.com",
        "Amsterdam, Netherlands",
        "FULL_TIME",
        True,
        False,
        "Build the internal platform that helps teams ship safely and consistently. The work spans cloud infrastructure, developer tooling, and measurable reliability improvements.",
        ("AWS", "Terraform", "Kubernetes", "Linux", "CI/CD"),
    ),
    (
        "Full Stack Developer",
        "employer.eu@example.com",
        "London, United Kingdom",
        "FULL_TIME",
        True,
        False,
        "Deliver customer-facing features from API to polished interface. You will collaborate closely with design and product while keeping quality and accessibility high.",
        ("TypeScript", "React", "Next.js", "Node.js", "REST APIs"),
    ),
    (
        "Data Engineer",
        "employer.eu@example.com",
        "Paris, France",
        "FULL_TIME",
        True,
        False,
        "Create trustworthy data pipelines and services for reporting and experimentation. Clear SQL, reliable operations, and thoughtful data contracts are central to the role.",
        ("Python", "SQL", "PostgreSQL", "AWS", "Docker"),
    ),
    (
        "Integration Engineer",
        "employer.eu@example.com",
        "Dublin, Ireland",
        "CONTRACT",
        True,
        False,
        "Connect partner systems through robust APIs and asynchronous workflows. You will translate business requirements into observable integrations with clear failure handling.",
        ("Python", "API Integration", "RabbitMQ", "Celery", "REST APIs"),
    ),
    (
        "Frontend Engineer",
        "employer.eu@example.com",
        "Hybrid - Berlin",
        "FULL_TIME",
        True,
        False,
        "Build responsive product experiences with a strong component architecture. Partner with backend and design teams to make complex workflows feel simple.",
        ("TypeScript", "React", "JavaScript", "Next.js", "API Integration"),
    ),
    (
        "DevOps Engineer",
        "employer.global@example.com",
        "Toronto, Canada",
        "FULL_TIME",
        True,
        False,
        "Improve delivery pipelines and production environments for several product teams. You will automate repeatable operations and make reliability visible through useful signals.",
        ("AWS", "Docker", "Kubernetes", "Terraform", "Linux", "CI/CD"),
    ),
    (
        "Cloud Engineer",
        "employer.global@example.com",
        "Dubai, United Arab Emirates",
        "FULL_TIME",
        True,
        False,
        "Help teams adopt secure, scalable cloud patterns across environments. The role balances hands-on infrastructure work with practical guidance and documentation.",
        ("Azure", "AWS", "Terraform", "Kubernetes", "Linux"),
    ),
    (
        "API Engineer",
        "employer.global@example.com",
        "Remote - Europe",
        "PART_TIME",
        False,
        False,
        "Maintain and extend a public API used by multiple client applications. This part-time role focuses on backward compatibility, documentation, and thoughtful API design.",
        ("Python", "Django REST Framework", "REST APIs", "PostgreSQL", "Git"),
    ),
    (
        "Software Architect",
        "employer.global@example.com",
        "Singapore",
        "FULL_TIME",
        False,
        True,
        "Set technical direction for a portfolio of connected services without losing sight of delivery. You will facilitate design reviews and help teams choose appropriately simple solutions.",
        ("System Design", "Microservices", "AWS", "PostgreSQL", "API Integration"),
    ),
    (
        "Cloud Platform Intern",
        "employer.global@example.com",
        "New York, United States",
        "INTERNSHIP",
        False,
        True,
        "Learn platform engineering by pairing with an experienced infrastructure team. You will contribute to small automation tasks, documentation, and safe improvements to developer workflows.",
        ("Python", "Docker", "Linux", "Git", "CI/CD"),
    ),
)

APPLICATION_SPECS = (
    ("candidate1@example.com", "Senior Django Developer", "APPLIED"),
    ("candidate2@example.com", "Senior Django Developer", "SHORTLISTED"),
    ("candidate3@example.com", "Senior Django Developer", "REJECTED"),
    ("candidate4@example.com", "Senior Django Developer", "HIRED"),
    ("candidate5@example.com", "Senior Django Developer", "APPLIED"),
    ("candidate6@example.com", "Airport IT Systems Engineer", "SHORTLISTED"),
    ("candidate7@example.com", "Airport IT Systems Engineer", "APPLIED"),
    ("candidate8@example.com", "Backend Engineer", "APPLIED"),
    ("candidate1@example.com", "Backend Engineer", "SHORTLISTED"),
    ("candidate2@example.com", "Backend Engineer", "APPLIED"),
    ("candidate3@example.com", "QA Automation Engineer", "REJECTED"),
    ("candidate4@example.com", "Technical Lead", "SHORTLISTED"),
    ("candidate5@example.com", "Technical Lead", "APPLIED"),
    ("candidate6@example.com", "Senior Backend Engineer", "HIRED"),
    ("candidate7@example.com", "Senior Backend Engineer", "SHORTLISTED"),
    ("candidate8@example.com", "Senior Backend Engineer", "APPLIED"),
    ("candidate1@example.com", "Platform Engineer", "REJECTED"),
    ("candidate2@example.com", "Platform Engineer", "APPLIED"),
    ("candidate3@example.com", "Full Stack Developer", "SHORTLISTED"),
    ("candidate4@example.com", "Full Stack Developer", "APPLIED"),
    ("candidate5@example.com", "Data Engineer", "REJECTED"),
    ("candidate6@example.com", "Data Engineer", "APPLIED"),
    ("candidate7@example.com", "Integration Engineer", "SHORTLISTED"),
    ("candidate8@example.com", "Integration Engineer", "APPLIED"),
    ("candidate1@example.com", "Frontend Engineer", "REJECTED"),
    ("candidate2@example.com", "DevOps Engineer", "APPLIED"),
    ("candidate3@example.com", "Cloud Engineer", "REJECTED"),
    ("candidate4@example.com", "Cloud Engineer", "APPLIED"),
)


def normalize_skill_name(name):
    return " ".join(name.split()).lower()


class Command(BaseCommand):
    help = "Create a deterministic, international demo recruitment dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete only known demo records before reseeding (DEBUG=True only).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            if not settings.DEBUG:
                raise CommandError("--reset is allowed only when DEBUG=True.")
            self.reset_demo_data()

        employers = self.seed_users(EMPLOYERS, User.Role.EMPLOYER)
        candidates = self.seed_users(CANDIDATES, User.Role.CANDIDATE)
        skills = {
            normalize_skill_name(name): Skill.objects.get_or_create(
                name=normalize_skill_name(name)
            )[0]
            for name in SKILL_NAMES
        }
        jobs = self.seed_jobs(employers, skills)
        applications = self.seed_applications(candidates, jobs)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {len(employers)} employers, {len(candidates)} candidates, "
                f"{len(skills)} skills, {len(jobs)} jobs, {applications} applications."
            )
        )

    def seed_users(self, users, role):
        result = {}
        for email, (first_name, last_name) in users.items():
            user, _ = User.objects.get_or_create(email=email, defaults={"role": role})
            user.role = role
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["role", "first_name", "last_name", "password"])
            result[email] = user
        return result

    def seed_jobs(self, employers, skills):
        jobs = {}
        for (
            title,
            employer_email,
            location,
            employment_type,
            active,
            deleted,
            description,
            job_skills,
        ) in JOB_SPECS:
            job, _ = Job.all_objects.update_or_create(
                employer=employers[employer_email],
                title=title,
                defaults={
                    "description": description,
                    "location": location,
                    "employment_type": employment_type,
                    "is_active": active and not deleted,
                    "deleted_at": timezone.now() if deleted else None,
                },
            )
            job.skills.set([skills[normalize_skill_name(name)] for name in job_skills])
            jobs[title] = job
        return jobs

    def seed_applications(self, candidates, jobs):
        count = 0
        for index, (candidate_email, job_title, status) in enumerate(APPLICATION_SPECS, start=1):
            Application.objects.update_or_create(
                candidate=candidates[candidate_email],
                job=jobs[job_title],
                defaults={
                    "status": status,
                    "cover_letter": f"I am excited to contribute to this team. Demo application {index}.",
                },
            )
            count += 1
        return count

    def reset_demo_data(self):
        demo_emails = tuple(EMPLOYERS) + tuple(CANDIDATES)
        demo_users = User.objects.filter(email__in=demo_emails)
        demo_jobs = Job.all_objects.filter(
            employer__email__in=EMPLOYERS,
            title__in=[spec[0] for spec in JOB_SPECS],
        )
        Application.objects.filter(candidate__in=demo_users).delete()
        Application.objects.filter(job__in=demo_jobs).delete()
        demo_jobs.delete()
        demo_users.delete()
        self.stdout.write("Known demo records reset.")
