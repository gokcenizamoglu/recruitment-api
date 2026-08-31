# Recruitment API

## Project Overview

Recruitment API is a focused Django REST Framework backend for a two-sided recruitment flow. Employers publish and manage jobs; candidates browse jobs, apply once per job, and review their own applications. The REST API is the primary product surface. Django Unfold admin is an additional operational and reviewer convenience, not a replacement for the API.

## Features

- Email-authenticated custom users with `EMPLOYER` and `CANDIDATE` roles
- JWT access/refresh authentication with refresh rotation and blacklist support
- Jobs, normalized reusable skills, configurable application questions, search, filtering, ordering, pagination, and soft deletion
- Candidate applications with optional protected resumes, typed answers, and serializer/database duplicate protection
- Employer-only applicant visibility and application status updates
- Health check, OpenAPI/Swagger, throttling, request IDs, CORS allow-list, and environment-based security settings
- Deterministic, idempotent demo data via `seed_demo`

## Tech Stack

Python 3.13, Django 5.2, Django REST Framework 3.16, PostgreSQL 16, SimpleJWT, django-filter, drf-spectacular, Django Unfold, WhiteNoise, pytest, Ruff, Docker Compose, and GitHub Actions. Dependency ranges are maintained in `requirements.txt` and `requirements-dev.txt`.

## Architecture and Data Model

The repository uses four focused Django areas: `accounts` (custom user and authentication), `jobs` (Job and Skill), `applications` (Application and workflow permissions), and `common` (health check, request-ID middleware, logging, and admin dashboard callback). Views and serializers are intentionally thin; no speculative service/repository layers are used.

```text
User (Employer) -> Jobs -> Applications <- User (Candidate)
                    |          |
                    v          v
                 Questions <- Answers
Jobs <-> Skills
```

`Job.employer` and `Application.candidate` are assigned from the authenticated request user. Skills are separate normalized records with a many-to-many relationship; comma-separated skill strings are not used. Optional resumes belong to the individual Application, while question text/type/options are snapshotted into submitted answers to preserve history.

## Authentication & User Flows

Both Employers and Candidates are authenticated platform users. They register, log in with email/password, and receive the same JWT token pair. Authorization then differs by role; separate `/candidate/login/` and `/employer/login/` endpoints are unnecessary because authentication is shared and authorization is role-based.

Candidate flow:

```text
Register -> Login -> Browse/Search Jobs -> Apply -> View Own Applications
```

Employer flow:

```text
Register -> Login -> Create/Manage Jobs -> View Applicants -> Update Application Status
```

Registration accepts `email`, `password`, `role`, and optional names. Public API role changes are not allowed. Passwords use Django hashing and the configured built-in validators. Use `Authorization: Bearer <access-token>` for protected requests.

SimpleJWT is configured with 15-minute access tokens, 7-day refresh tokens, rotation, and blacklist-after-rotation. Registration and token endpoints use dedicated lightweight throttles (`10/hour` and `20/hour` respectively).

## Setup

### Docker (recommended)

```bash
git clone https://github.com/gokcenizamoglu/recruitment-api.git
cd recruitment-api
cp .env.example .env
docker compose up --build
```

The Compose project starts PostgreSQL 16 and a web container. The web container waits for the healthy database, runs migrations, collects static files, and starts Gunicorn on port 8000. Open `http://localhost:8000`; set `WEB_PORT` in `.env` if the host port is occupied.

## Reviewer Quick Start

```bash
git clone https://github.com/gokcenizamoglu/recruitment-api.git
cd recruitment-api
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py seed_demo
```

Open Swagger at `http://localhost:8000/api/docs/`, log in with a local demo Employer or Candidate account from the [Demo Data](#demo-data) section, and use the returned JWT with Swagger’s **Authorize** button. Optionally create a superuser and inspect `/admin/`.

### Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

If `POSTGRES_HOST` is unset, settings use SQLite for a simple local workflow. Set PostgreSQL variables in `.env` to run locally against PostgreSQL.

## Environment Variables

`.env.example` documents `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, PostgreSQL connection values, `CORS_ALLOWED_ORIGINS`, logging, proxy, cookie, SSL redirect, and HSTS settings. Development defaults are HTTP-friendly. Production deployments must use a unique secret, `DEBUG=false`, explicit hosts, HTTPS, secure cookies, and non-zero HSTS values. Never commit real credentials.

## Administrative Interface

Django Unfold provides the internal admin at `/admin/`. Create a reviewer account with:

```bash
python manage.py createsuperuser
# Docker
docker compose exec web python manage.py createsuperuser
```

Staff can inspect users, jobs, skills, and applications. Soft-deleted jobs remain visible in admin through the all-records queryset, with deleted-state filters and a restore action. Job and Skill lists show related application/job counts where applicable. Application deletion is disabled to preserve recruitment history. The dashboard displays employer, candidate, job, active-job, application, status-distribution, and recent-application metrics. The REST API remains the primary interface.

## API Inventory

All API routes are under `/api/v1/` unless noted.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register/` | Public | Register Employer or Candidate |
| POST | `/auth/token/` | Public | Email/password login; returns JWT pair |
| POST | `/auth/token/refresh/` | Public | Rotate a refresh token |
| GET | `/auth/me/` | Authenticated | Return current user |
| GET | `/skills/` | Authenticated | List normalized skills |
| POST | `/skills/` | Employer | Create a skill |
| GET | `/jobs/` | Authenticated | List visible, non-deleted jobs |
| POST | `/jobs/` | Employer | Create a job owned by request user |
| GET | `/jobs/{id}/` | Authenticated | Retrieve a visible job |
| PUT/PATCH | `/jobs/{id}/` | Owning Employer | Update own job |
| DELETE | `/jobs/{id}/` | Owning Employer | Soft-delete own job; returns 204 |
| GET | `/jobs/{id}/applications/` | Owning Employer | Paginated applicants for own non-deleted job |
| GET/POST | `/jobs/{id}/questions/` | Authenticated / Owning Employer | List active questions or create an owned Job question |
| GET/PATCH/DELETE | `/jobs/{id}/questions/{question_id}/` | Authenticated / Owning Employer | Read, update, or deactivate a Job question |
| GET | `/applications/` | Authenticated | Candidate’s own or employer-managed applications |
| POST | `/applications/` | Candidate | Atomically apply with optional resume and answers |
| PATCH | `/applications/{id}/status/` | Owning Employer | Update status for own job’s application |
| GET | `/applications/{id}/resume/` | Candidate owner, owning Employer, or staff | Protected resume download |
| GET | `/health/` | Public | Check application and database reachability |
| GET | `/api/schema/` | Public | OpenAPI schema |
| GET | `/api/docs/` | Public | Swagger UI with Bearer authorization |

`/skills/` is read/create only; there are no skill update/delete routes. Application deletion is intentionally not exposed.

## Search and Filtering

`GET /api/v1/jobs/` supports DRF filter backends and page-number pagination (20 items by default):

```text
/api/v1/jobs/?search=django
/api/v1/jobs/?location=Istanbul
/api/v1/jobs/?skills=1&skills=3
/api/v1/jobs/?employment_type=FULL_TIME&is_active=true
/api/v1/jobs/?ordering=-created_at
```

`search` covers title and description. Supported ordering fields are `created_at`, `updated_at`, and `title`; prefix a field with `-` for descending order. `skills` filters by skill IDs.

## Permissions and Business Rules

- Employers create jobs and can update/delete only their own jobs. Employer IDs are never accepted from client input.
- Candidates can view/search jobs but cannot create, update, or delete them.
- Candidates can apply only to active, non-deleted jobs. Candidate identity is always the authenticated user.
- Active required Job questions must be answered during submission; answer types, question ownership, activity, and configured choices are validated atomically.
- A candidate cannot apply to the same job twice; serializer validation provides a clear error and the database `UniqueConstraint(job, candidate)` protects against races.
- Candidates see only their own applications. Employers see and manage applications only for their own jobs.
- Submitted resumes and answers are immutable. Question deletion through the API deactivates the question, and historical answers use snapshots rather than editable current wording.
- Candidates cannot change application status. Employers can set `APPLIED`, `SHORTLISTED`, `REJECTED`, or `HIRED` for applications belonging to their jobs.
- Job ownership, candidate/employer identities, timestamps, status-at-creation, and deletion fields are server controlled.

## Soft Delete and History

Deleting a job performs normal REST behavior and returns HTTP 204, but internally sets `deleted_at` and `is_active=False`. Public job querysets hide deleted jobs; admin uses `Job.all_objects` so archived jobs remain inspectable and restorable. `PROTECT` foreign keys avoid silently removing referenced recruitment history. Current limitation: employer application querysets exclude applications whose jobs are soft-deleted, so archived-job applications are currently administrative-only in this assignment scope.

## Optional Product Enhancement: Secure Application Documents and Questions

These capabilities are production-minded enhancements beyond the original technical assignment.

Candidates may attach one optional resume to an Application. Accepted formats are PDF, DOC, and DOCX with a maximum size of 5 MiB. Validation checks size, final extension, client MIME as a secondary signal, and lightweight file/container signatures. Storage uses private UUID-based names under `private_media`; Docker persists that directory in a named volume. There is deliberately no public media route and API responses never expose storage paths or `FileField.url` values.

Resume access is always authorized through `GET /api/v1/applications/{id}/resume/`. The submitting Candidate, the Employer who owns the Application’s Job (including after soft deletion), and authenticated staff may download it. Unrelated authenticated users receive 404. Downloads are attachments with no-sniff and private/no-store response headers.

Employers can define `TEXT`, `TEXTAREA`, `NUMBER`, `BOOLEAN`, and `SINGLE_CHOICE` questions for their own Jobs. Single-choice options are a validated JSON list containing 2-20 unique, non-empty labels. Candidates see active questions. All active required questions must be answered, and submitted question IDs must be active and belong to the selected Job.

JSON clients may continue creating an Application with the original request shape. JSON requests can additionally send `answers` as an array. To attach a resume, submit `multipart/form-data`; in multipart, `answers` is a JSON-encoded array string:

```text
job=42
cover_letter=I would like to apply.
resume=<binary PDF/DOC/DOCX>
answers=[{"question":3,"value":5},{"question":4,"value":true},{"question":5,"value":"Remote"}]
```

Application, resume, and answers are created as one submission. Submitted content cannot be edited or replaced. Employers may edit question wording for future applicants, but answer responses retain snapshot text, type, and choice options. Once answers exist, a question’s type cannot change; deleting it through the API only marks it inactive.

File signature validation is intentionally lightweight. Malware scanning, private cloud object storage, and short-lived signed URLs remain production evolution considerations rather than local assignment infrastructure.

## Security Considerations

JWT authentication, password validators, role permissions, object ownership checks, queryset isolation, protected resume delivery, and server-controlled identity/snapshot fields protect the API against common IDOR and mass-assignment mistakes. Refresh rotation and blacklisting reduce token replay. CORS is allow-list based and credentials are not enabled. Registration/login throttles are configured without adding Redis. Request IDs and structured logging are enabled; passwords, authorization headers, JWT values, file contents, and private storage paths are not logged. `X-Frame-Options=DENY` and content-type sniffing protection are enabled. SSL redirect, secure cookies, proxy TLS trust, and HSTS are environment controlled so local HTTP remains convenient while CI and production can enable hardened values. The health endpoint reports only status, not connection details.

## Demo Data

```bash
python manage.py seed_demo
python manage.py seed_demo --reset  # DEBUG=True only
```

The managed deterministic dataset contains:

- 3 employers
- 8 candidates
- 27 normalized skills
- 16 jobs
- 28 applications

It includes international locations (including several Istanbul entries), all four application statuses, active jobs, inactive jobs, and soft-deleted jobs. Demo accounts use `DemoPass123!` and are **local development-only credentials**:

- Employers: `employer.istanbul@example.com`, `employer.eu@example.com`, `employer.global@example.com`
- Candidates: `candidate1@example.com` through `candidate8@example.com`

The command is safe to rerun. `--reset` is guarded by `DEBUG` and targets only curated managed demo users/jobs and exact deterministic application identities; it does not delete arbitrary records belonging to a demo candidate. Skills are reusable catalog data and are not broadly deleted.

## Testing and Quality

```bash
pytest tests --cov=. --cov-report=term-missing
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py check --deploy
```

The normal local `.env` keeps HTTP development convenient, so `check --deploy` may report expected warnings when run with those defaults. CI runs it with production-like values enabled, including `DEBUG=False`, a strong CI-only `SECRET_KEY`, appropriate hosts, HTTPS redirect, secure cookies, and HSTS.

The current suite covers authentication, JWT refresh rotation/blacklisting, throttling, health, job ownership and soft deletion, filtering, applications and serializer/database duplicate protection, secure resume validation/access, question ownership and typed answers, snapshot history, skill normalization, admin behavior, and seed idempotency/reset safety. The latest full run contains 54 tests with 95% coverage. GitHub Actions runs Ruff, migration drift checks, Django checks, the deployment security check with production-like environment values, and pytest against PostgreSQL.

## Design Decisions

- A custom User model makes email the stable identifier and avoids a later authentication migration.
- Email login is shared by both roles; authorization is role-based rather than duplicated into separate login APIs.
- Skill is a normalized model so the catalog is reusable and filterable instead of comma-separated text.
- TextChoices keeps genuinely fixed employment/status vocabularies explicit and validated.
- Duplicate applications are checked at both serializer and database levels for usability and race safety.
- Resumes remain private Application-specific submission artifacts; answers snapshot editable question definitions to preserve the original meaning.
- Jobs use targeted soft deletion to preserve history without introducing a generic deletion framework.
- Applications have no public delete operation because recruitment history should remain auditable.
- The code uses normal Django app boundaries without speculative repository/service/infrastructure layers.
- Multi-tenancy and SaaS billing were intentionally excluded from this assignment’s scope.

## Future SaaS Evolution (Not Implemented)

Possible future capabilities include organizations/tenants, companies and departments, tenant memberships, custom RBAC, configurable recruitment pipelines and interview stages, interview scheduling, reusable CV libraries, multiple attachments, private cloud object storage with signed URLs, malware scanning, AI CV parsing/scoring, `MULTIPLE_CHOICE` questions, full form versioning or an advanced form builder, offers, notifications and email integration, Celery with Redis/RabbitMQ, audit logs, analytics, subscription plans and billing, feature flags, webhooks, SSO, and KVKK/GDPR-oriented data lifecycle management.

Future domain events could include `application_created` and `application_status_changed`. In a production SaaS, notification consumers should normally process those events asynchronously rather than sending external email inside the request-response cycle. None of these future features or placeholder event/notification modules are implemented here.

## Repository Layout

```text
config/                  Django settings, URLs, ASGI/WSGI
accounts/                Custom User, auth serializers/views/admin
jobs/                    Job, Skill, filters, permissions, seed command/admin
applications/            Applications, answers, private resumes, serializers, views/admin
common/                  health endpoint, request IDs, logging, dashboard
tests/                   pytest suite and shared fixtures
.github/workflows/ci.yml CI checks with PostgreSQL service
Dockerfile               Gunicorn container image
docker-compose.yml       PostgreSQL + web development stack
```
