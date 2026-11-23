# EKLAVYA · एकलव्य

**Learn. Practice. Master.**

EKLAVYA is a full-stack learning and competitive-practice platform for programming, DSA, SQL, Pandas, NumPy, statistics, distributed processing, machine learning, and deep learning. It combines structured Vidya Paths and Daily Sadhana with an isolated judge, verified progression, and timed Arena contests.

## Capabilities

- 20 original, seeded challenges across six subject areas and six response formats.
- FastAPI API, PostgreSQL persistence, versioned Alembic migrations, Redis, and Celery workers.
- Argon2 password hashing, short-lived JWT access tokens, one-way refresh-token rotation, protected profile routes, role checks, one-time verification/reset tokens, and server-side HTTP-only cookies.
- Monaco workspaces for Python, Java, C, C++, and SQL plus accessible numerical and multiple-choice inputs.
- Isolated Docker execution with no network, a read-only root filesystem, dropped capabilities, process/CPU/memory/time/output limits, and disposable filesystems.
- Dedicated SQL, Pandas, NumPy, PySpark, MapReduce, scikit-learn, and PyTorch evaluators.
- Verified XP transactions, six Maharathi ranks, Veer achievements, leaderboards, insights, Daily Sadhana streaks, and 14 Vidya Paths.
- Timed Arena registration, problem embargoes, contest-scoped submissions, ICPC-style penalties, rating history, and idempotent finalization.
- A database-authorized admin control center for problems, private datasets, users, contests, paths, achievements, XP/rank review, and append-only action history.
- Server-timed assessments with student/group assignment, attempt limits, autosave, secure-judge answers, idempotent finalization, analytics, templates, and CSV/XLSX result export.
- A private Data Cleaning Lab for CSV, XLSX, JSON, and Parquet profiling, bounded transformations, cleaned downloads, and isolated Pandas, NumPy, or SQL experimentation.
- Documented-subset Excel and Tableau expression graders, isolated Linux/Bash challenges, multi-tool analytical practice, a versioned dataset library, and skill-wise analytics.
- Bounded public-data caching, explicit database pools, indexed/paginated hot paths, judge leases/cancellation/recovery, and measured load-test tooling.
- Production configuration validation, allowlisted hosts/origins, security headers, Redis rate limits, request IDs, JSON logs, health probes, metrics, hardened containers, and an Nginx deployment edge.

## Architecture

| Component | Responsibility |
|---|---|
| `frontend/` | Next.js App Router, TypeScript, Tailwind CSS, Recharts, self-hosted Monaco, and BFF routes that hold tokens in HTTP-only cookies |
| `backend/app/` | FastAPI endpoints, authorization, SQLAlchemy models, progression, contests, operational middleware, and seed command |
| `backend/alembic/` | Ordered, reversible PostgreSQL/SQLite schema migrations |
| `judge/` | Celery worker, generic Docker executor, specialized evaluators, and minimal runner images |
| `challenges/` | Public catalog, private test fixtures, evaluator contracts, progression, and learning-path definitions |
| `infrastructure/` | Production reverse-proxy configuration |
| `scripts/` | Guarded PostgreSQL backup and disposable-restore tooling |
| `.github/workflows/` | API, migration, browser, dependency, container, and Compose verification |

The API never executes learner code. It stores and queues a submission; the judge runs a new restricted container for each evaluation and persists only the bounded result. Hidden cases are stored separately and never appear in public schemas.

## Quick start

Docker Engine and Compose v2 are required. Copy the development settings, then start either the complete platform or the lighter core stack.

```sh
cp .env.example .env
docker compose --profile judge up --build -d --wait
```

### Docker Desktop on macOS (trusted local development)

On Docker Desktop installations where the judge socket is owned by root and
cannot be accessed by its unprivileged user, **do not** change the socket
permissions. Use the explicit local-only override, which grants the worker
Docker daemon control and must never be used on a public server:

```sh
docker compose -p eklavya -f docker-compose.yml -f docker-compose.judge-local.yml --profile judge up -d --build
bash scripts/verify_judge_local.sh
```

Open <http://localhost:3000>. The API listens on the port set by
`BACKEND_PORT` in `.env` (8001 in the verified macOS setup).

The repair has passed 22 local judge smoke tests, including Java, C++, SQL,
Pandas/NumPy, PySpark, PyTorch, error outcomes, and output/time limits.
This does **not** mean the Docker-socket design is production-secure, nor does
it validate every browser/account workflow. See
[local judge setup and security notes](docs/LOCAL_JUDGE_DOCKER.md).

The full command builds the data, Spark, ML, and CPU PyTorch images and can take several minutes. For UI/API work without execution workers:

```sh
docker compose up --build -d --wait
```

Open <http://localhost:3000>. The development API documentation is at <http://localhost:8000/docs>. The one-shot `migrate` service applies all migrations and idempotently seeds problems, ranks, paths, the daily challenge, and the weekly contest before the API starts.

On Windows, double-click `start.bat` to create the local `.env` when needed, start the complete platform with isolated judge workers, wait for readiness, and open the site. The first run builds the larger scientific, Spark, and AI images and can take several minutes. Run `start.bat web` from Command Prompt only when you want the lightweight UI/API stack without code execution or working submissions.

Useful commands:

```sh
make up          # complete stack, including judge profiles
make up-core     # frontend, API, PostgreSQL, and Redis
make logs
make down
```

Never use the example PostgreSQL password or development secret in an exposed environment.

### Provision an administrator

Public registration cannot choose an administrative role. Create or promote an administrator only from a trusted host:

```sh
PYTHONPATH=. python -m backend.app.provision_admin --email admin@example.com --username admin --display-name "Platform Administrator"
```

The command prompts for a password without echoing it. Automation may inject `EKLAVYA_ADMIN_PASSWORD` from a secret manager for the duration of the command. After signing in, open `/admin`.

## Host development

Requires Python 3.12, Node.js 24, PostgreSQL 17, and Redis 7.

```sh
cp .env.example .env
docker compose up -d --wait db redis
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Set `API_BASE_URL` in `frontend/.env.local` when the API is not at `http://127.0.0.1:8000/api/v1`. To execute submissions from a host worker, Docker must also be available and the four specialized images must be built with the names in `docker-compose.yml`.

## Configuration

The root `.env.example` documents development defaults. Important production settings are:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Unpredictable JWT signing key, at least 32 characters |
| `PRODUCTION_DATABASE_URL` | PostgreSQL URL used by API, migration, and judge services |
| `ALLOWED_ORIGINS` | Comma-separated browser-origin allowlist; wildcards are rejected in production |
| `ALLOWED_HOSTS` | Comma-separated public hosts plus the internal `backend` hostname |
| `COOKIE_SECURE` | Must be `true` behind HTTPS |
| `RATE_LIMIT_ENABLED` | Enables shared Redis fixed-window limits |
| `READINESS_CHECK_REDIS` | Includes Redis in readiness checks |
| `DATASET_STORAGE_DIR` | Private mounted storage for hidden administrator datasets |
| `DATASET_MAX_BYTES` | Maximum accepted administrator dataset upload size |
| `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` | Per-process PostgreSQL pool budget |
| `PUBLIC_CACHE_SECONDS` | Shared Redis TTL for public, non-user-specific responses |
| `JUDGE_STUCK_SECONDS` | Age at which an administrator may recover a running judge lease |

Production additionally requires an authenticated `PRODUCTION_REDIS_URL`, matching `REDIS_PASSWORD`, an HTTPS `PUBLIC_URL`, and enabled shared rate limits/readiness checks. Start from `.env.production.example`; never commit the completed file.

Starting the API with `ENVIRONMENT=production` and a development secret, wildcard origin, or wildcard host fails immediately.

## API overview

All application routes use `/api/v1`.

| Area | Routes |
|---|---|
| Operations | `GET /health`, `/health/live`, `/health/ready`, `/metrics` |
| Catalog | `GET /problems`, `GET /problems/{slug}` |
| Accounts | `POST /auth/register`, `/login`, `/refresh`, `/logout`, verification/reset routes; `GET/PATCH /auth/me` |
| Submissions | `POST /problems/{slug}/submissions`, `GET /submissions`, `GET /submissions/{id}`, `POST /submissions/{id}/cancel` |
| Progression | `GET /gamification/ranks`, `/leaderboard`, protected dashboard, achievements, and insights |
| Learning | Daily challenge/history plus path list, detail, and enrollment routes |
| Arena | Contest list/detail, registration, participant status, submissions, leaderboard, rating history, and admin finalization |
| Advanced practice | Assigned assessments, attempts/autosave/finalization, Data Lab, Excel/Tableau graders, Linux catalog, multi-tool challenges, dataset library, and skill analytics under `/advanced/*` |
| Administration | Overview, problem/dataset/user/contest/path/achievement management, XP/rank review, and audit history under `/admin/*` |

Administrator-only APIs manage private cases, evaluation datasets, platform content, accounts, and operating history. Public registration can never select an administrator role.

## Verification

Run the same core checks as CI from the repository root:

```sh
source .venv/bin/activate
PYTHONPATH=. pytest -q backend/tests judge/tests

cd frontend
npm ci
npm audit --omit=dev --audit-level=high
npm run typecheck
npm run build
npx playwright install chromium
npm test
```

Migration verification should use a disposable database:

```sh
cd backend
alembic upgrade head
alembic check
alembic downgrade base
alembic upgrade head
```

CI additionally validates every Dockerfile and smoke-tests the core Compose stack. Heavy evaluator images are profile-gated so routine pull requests do not repeatedly download Spark and PyTorch, while their Dockerfiles and evaluator contracts remain checked.

Bounded local performance checks must target disposable infrastructure:

```sh
python performance/benchmark.py --base-url http://127.0.0.1:8000/api/v1 --requests 500 --concurrency 20
pip install -r performance/requirements.txt
locust -f performance/locustfile.py --headless --users 10 --spawn-rate 2 --run-time 20s --host http://127.0.0.1:8000
```

See [the Phase 15 report](docs/PHASE15_PERFORMANCE_REPORT.md) for the measured environment, before/after results, query plans, and limitations. Never direct these workloads at production without an approved test window.

## Production deployment

`docker-compose.prod.yml` is an override for a single-host deployment. It removes direct database/API/frontend ports, enables secure cookies and shared rate limits, authenticates Redis, segments application/data networks, applies resource/log limits, makes secrets mandatory, and exposes only an unprivileged Nginx proxy on loopback port 8080.

```sh
docker compose --env-file /secure/path/eklavya.env -f docker-compose.yml -f docker-compose.prod.yml --profile judge config
docker compose --env-file /secure/path/eklavya.env -f docker-compose.yml -f docker-compose.prod.yml --profile judge up --build -d --wait
```

Terminate TLS at a managed load balancer or host proxy in front of `127.0.0.1:8080`. Do not expose that HTTP listener directly. `docker-compose.tls.yml` and `infrastructure/nginx-tls.conf` provide an optional direct-TLS path with operator-supplied files. Apply database backups before upgrades and run the one-shot migration service before scaling new API or judge replicas.

Documentation: [architecture](docs/architecture.md), [API](docs/api.md), [database](docs/database.md), [judge](docs/judge.md), [security](docs/security.md), [deployment/rollback](docs/deployment.md), [operations](docs/operations.md), and [troubleshooting](docs/troubleshooting.md).

Release evidence: [Phase 16 readiness](docs/PHASE16_RELEASE_READINESS.md) and the [final verification report](docs/EKLAVYA_FINAL_VERIFICATION_REPORT.md).

## Honest security boundary and limitations

- Judge containers enforce and unit-test the configured isolation flags, but Docker-socket access makes the judge service a privileged infrastructure boundary. Run it on a dedicated, patched host or replace it with an external sandbox service before accepting hostile public traffic. The project has not received an independent penetration test.
- Verification and password-reset tokens are created, hashed, expired, and consumed safely, but an email provider adapter is intentionally not bundled. Production must deliver the opaque token through a transactional email service; raw tokens are never written to logs.
- The seed catalog is representative curriculum, not a complete course library. Large learner datasets should move to object storage rather than database test-case fields.
- Excel grading supports a documented formula subset and finite ranges; VLOOKUP/HLOOKUP and workbook features that require a complete Excel calculation engine are administrator-reviewed. Tableau grading supports documented aggregates, FIXED LOD, running/window calculations, and explicit partition/order context, not the complete Tableau runtime.
- Data Lab storage is private local-volume storage for single-host deployments. Multi-host production must replace it with private object storage and lifecycle policies; Data Lab code still runs only in disposable judge containers.
- In-memory metrics reset on process restart. A production collector should scrape each replica and retain time series externally.
- The dashboard keeps a clearly labeled demo comparison panel for new visitors; authenticated progression, schedules, paths, and contest data are live.
