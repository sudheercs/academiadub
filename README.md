# AcademiaHub

> An academic portal for structured learning — read, practise, run code, download materials.

**Blueprint v2 · Sep 2026**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Django REST Framework (Python 3.12) |
| Frontend | Next.js 14 (TypeScript) |
| Database | MySQL 8.0.11+ (server-hosted) |
| Cache / Sessions | Redis 7 |
| Object Storage | AWS S3 (ap-south-1) |
| Email | AWS SES |
| Dev environment | Docker Compose |
| Production | AWS ECS/Fargate — ap-south-1 Mumbai |

---

## Getting Started (local dev)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- `make` available (`brew install make` on macOS if needed)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/academiadub.git
cd academiadub
cp .env.example .env
# Edit .env and set SECRET_KEY to a random 50+ character string
# Set DATABASE_URL to your MySQL server credentials
```

The API requires a MySQL `DATABASE_URL` in `.env`; SQLite and a local database
container are not used. URL-encode special characters in the username or
password, and ensure the MySQL server permits connections from your host.
Keep `.env` private and never commit credentials.

### 2. Start all services

```bash
make dev
# or: docker compose -f infra/docker-compose.yml up --build
```

| Service | URL |
|---|---|
| Next.js frontend | http://localhost:3000 |
| Django API | http://localhost:8000 |
| API health check | http://localhost:8000/api/health/ |
| Django admin | http://localhost:8000/admin/ |
| Redis | localhost:6379 |
| Code execution | Through the API at http://localhost:8000/api/codelab/run/ (runner is private) |

Browser login uses HttpOnly access and refresh cookies. For production deployments
where the frontend and API use separate subdomains, set `AUTH_COOKIE_DOMAIN` to
their shared parent domain (for example, `.academiadub.in`) and configure
`CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` for the frontend URL. Leave
the cookie domain blank for local development.

### 3. Create a superuser

```bash
make createsuperuser
```

---

## Common Commands

```bash
make dev              # Start everything
make stop             # Stop everything
make migrate          # Run DB migrations
make makemigrations   # Create new migrations
make test-backend     # Run Django test suite
make lint             # Lint backend + frontend
make shell            # Django shell
make logs             # Follow all container logs
make help             # Show all commands
```

---

## Project Structure

```
academiadub/
├── backend/          # Django REST Framework API
│   ├── academiadub/  # Project settings, urls, wsgi/asgi
│   └── apps/         # Feature modules (identity, catalogue, content …)
├── frontend/         # Next.js 14 app
│   ├── app/          # App Router pages
│   ├── components/   # Shared UI components
│   └── design-system/# CSS tokens and base components
├── coderunner/       # Isolated Python/JavaScript execution service
├── infra/            # Docker Compose, AWS task definitions
├── docs/             # Threat model, ADRs, runbooks
└── .github/workflows/# CI and deploy pipelines
```

---

## Roadmap

| Phase | Scope | Duration |
|---|---|---|
| **0. Foundations** ← *you are here* | Repo, Docker, CI/CD, design system | 2 wks |
| 1. Identity | Auth, MFA, roles, permissions | 3 wks |
| 2. Catalogue & reader | Subjects, topics, blocks, search, progress | 4 wks |
| 3. CMS & workflow | Editor UI, versioning, review/publish, audit log | 4 wks |
| 4. Downloads | File registry, signed links, virus scan | 2 wks |
| 5. Practice & Code Lab | Quizzes, Python & JS sandbox | 5 wks |
| 6. Classes & analytics | Instructor tools, assignments, reports | 3 wks |
| 7. Hardening & launch | Load test, security audit, accessibility | 3 wks |
| 8. Later | Payments, community, mobile, AI tutor | TBD |

---

## Contributing

1. Branch off `main`: `git checkout -b feat/your-feature`
2. Run `make lint` before pushing
3. Open a PR — CI must pass before review
4. One approval required to merge to `main`

---

## License

Proprietary — all rights reserved.
