# Recruitment API

## Project Overview

Recruitment API is a small Django + Django REST Framework service for employers publishing jobs and candidates applying to them. It is intentionally a focused assignment-sized backend with production-minded defaults and clear extension points.

## Features

- Email-based custom users with employer/candidate roles
- JWT authentication with rotating, blacklisted refresh tokens
- Jobs, normalized skills, soft deletion, search, filters, ordering, and pagination
- Candidate applications with duplicate protection at API and database levels
- Employer-only application review and status updates
- Health check, OpenAPI/Swagger, throttling, request IDs, environment-aware security
- Repeatable demo seed command

## Tech Stack

Python 3.13, Django 5.2, Django REST Framework, PostgreSQL, SimpleJWT, django-filter, drf-spectacular, pytest, Ruff, Docker Compose, and GitHub Actions.

## Architecture and Data Model

The project uses `accounts`, `jobs`, and `applications` Django apps. Views and serializers remain thin; business rules live close to the models/serializers and reusable permissions. `User` has email, role, and profile fields. `Job` belongs to an employer and has a many-to-many `Skill` relation. `Application` references a job and candidate and has a fixed `Status` TextChoices enum.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Without `POSTGRES_HOST`, settings use SQLite for a simple local/test workflow. Docker and CI configure PostgreSQL.

## Environment Variables

See `.env.example` for secret key, debug/hosts, PostgreSQL, CORS, proxy, cookie, HSTS, and logging settings. Never commit real credentials.

## Docker Usage

```bash
cp .env.example .env
docker compose up --build
```

The web container waits for the healthy PostgreSQL service, runs migrations, collects static files, and serves on `http://localhost:8000`.

## Authentication

Register with `POST /api/v1/auth/register/` using `email`, `password`, `role`, and optional names. Obtain tokens at `POST /api/v1/auth/token/`, refresh at `/api/v1/auth/token/refresh/`, and inspect the authenticated user at `GET /api/v1/auth/me/`. Send `Authorization: Bearer <access-token>`.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register/` | Register |
| POST | `/api/v1/auth/token/` | Login |
| POST | `/api/v1/auth/token/refresh/` | Rotate refresh token |
| GET | `/api/v1/auth/me/` | Current user |
| GET/POST | `/api/v1/skills/` | List/create skills (employer create) |
| GET/POST | `/api/v1/jobs/` | List/create jobs |
| GET/PATCH/DELETE | `/api/v1/jobs/{id}/` | Read/update/soft-delete a job |
| GET | `/api/v1/jobs/{id}/applications/` | Employer's job applicants |
| GET/POST | `/api/v1/applications/` | List own/managed applications or apply |
| PATCH | `/api/v1/applications/{id}/status/` | Employer changes status |
| GET | `/api/v1/health/` | Application/database health |
| GET | `/api/schema/` and `/api/docs/` | OpenAPI and Swagger UI |

## Search and Filtering

Jobs support `search` (title/description), `location`, `skills` (skill IDs, repeatable), `employment_type`, `is_active`, `ordering` (`created_at`, `updated_at`, `title`, prefix with `-`), and page pagination.

## Permissions and Business Rules

Employers create and manage only their own jobs; candidates have read-only job access. Candidates apply only to active, non-deleted jobs and see only their applications. Employers see applications for their own jobs and can update their status. Applications are not deletable. Employer/candidate ownership fields, timestamps, role, and soft-delete fields are server controlled. Job deletion sets `deleted_at` and `is_active=False`, while public querysets hide deleted jobs.

## Testing and Quality

```bash
pytest --cov=.
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py check --deploy
```

The CI workflow runs all of the above against PostgreSQL.

## Security Considerations and Design Decisions

A custom User model avoids a costly future migration and makes email the stable login identifier. Skills are separate normalized records so jobs can be filtered and indexed without comma-separated data. Duplicate applications are checked in the serializer for a friendly error and protected by a database `UniqueConstraint` for race safety. Jobs use targeted soft deletion to retain recruitment history; a generic deletion framework would add complexity without value here. Applications are immutable records from a workflow/audit perspective, so there is no public delete endpoint. Status uses `TextChoices` to keep the fixed business vocabulary explicit and validated.

Refresh rotation and blacklisting limit token replay. Authentication errors remain generic, passwords/tokens are never logged, throttles protect registration/login, CORS is allow-list based, and production security flags are environment controlled. `PROTECT` foreign keys preserve job/application history when users or jobs are referenced.

## Demo Data

`python manage.py seed_demo` creates employer/candidate accounts (`employer@example.com`, `candidate@example.com`, password `DemoPassword123!`), skills, and several jobs. It is safe to rerun for the same demo records.

## Administrative Interface

The internal Django admin uses Django Unfold for a restrained, domain-specific operational experience. The REST API remains the primary assignment interface; the admin is intended for reviewer and operations convenience. Staff users can inspect users, jobs, applications, skills, and soft-deleted jobs. Privileged admins can restore soft-deleted jobs from the Job changelist. Application history is intentionally preserved, so Application deletion is disabled in admin.

## Future SaaS Evolution

This assignment intentionally does not implement organizations/tenants, companies/departments, memberships, custom roles, pipelines/stages, interview scheduling, CV storage, offers, notifications, email integration, Celery jobs, audit logs, analytics, subscriptions/billing, feature flags, webhooks, SSO, or KVKK/GDPR lifecycle tooling. A later SaaS version could add an Organization and membership boundary first, then tenant-scoped querysets, configurable pipelines/interviews, storage and asynchronous integrations. Domain events such as `application_created` and `application_status_changed` could feed a Celery-backed notification worker; external email should normally be sent asynchronously outside the request-response cycle. These are documented evolution paths, not unused placeholder code in this project.
