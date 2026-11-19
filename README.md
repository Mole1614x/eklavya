# EKLAVYA · एकलव्य

**Learn. Practice. Master.**

EKLAVYA is a practice platform for programming, algorithms, data, statistics, and AI. Phase 1 provides the application foundation and a browsable, database-backed catalog.

## Start with Docker Compose

Install Docker with Compose v2, then run from the repository root.

```sh
cp .env.example .env
docker compose up --build -d --wait
```

Open the frontend at <http://localhost:3000>, the dashboard at <http://localhost:3000/dashboard>, and the API docs at <http://localhost:8000/docs>. Compose applies database migrations and seeds the catalog on backend startup. The database volume persists across `docker compose down`.

The sample credentials are for local development. If you change the PostgreSQL credentials or database name, update `COMPOSE_DATABASE_URL` to match for Compose and `DATABASE_URL` to match for host development. Compose accepts `FRONTEND_PORT`, `BACKEND_PORT`, and `POSTGRES_PORT` overrides. An existing PostgreSQL volume retains its original users and credentials.

## Develop on the host

Requires Node.js 24, Python 3.12, and PostgreSQL 17. Use Compose to run just the database if needed.

```sh
cp .env.example .env
docker compose up -d --wait db
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

In a second terminal from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

The frontend makes server-side API requests. Set `API_BASE_URL` in `frontend/.env.local` for a custom backend during frontend development. The backend reads its settings from environment variables and the root `.env`.

## What Phase 1 includes

- Homepage, dashboard, catalog, six practice modules, and six community previews.
- Catalog search by title or topic, category/difficulty/topic filters, pagination, and detail pages.
- Self-hosted Monaco with per-language drafts for programming exercises, a radio group for multiple choice, and a numeric input for numerical exercises. Drafts live in the open workspace.
- Dashboard with demo XP, rank, streak, solved count, and practice activity. The featured exercise and catalog entries use real seeded records.
- 20 original challenges: 4 Foundations (2 logic and 2 patterns), 3 DSA, 5 Data (2 SQL, 2 Pandas, 1 NumPy), 3 Statistics, 2 Big Data (PySpark and MapReduce), and 3 AI (2 machine learning and 1 deep learning).

Run and Submit show explicit unavailable states. Accounts, judging, grading, saved submissions, XP awards, scheduled daily challenges, contests, and stored learner progress are planned for later phases. The sample pattern statements specify exact interior spacing and permit an optional final newline. The judge phase will implement and verify comparison rules.

## Architecture

| Directory | Responsibility |
|---|---|
| `frontend/` | Next.js App Router, TypeScript, Tailwind CSS, Recharts, Monaco, Playwright |
| `backend/app/` | FastAPI endpoints, settings, typed schemas, SQLAlchemy models, catalog queries, seed command |
| `backend/alembic/` | Versioned PostgreSQL migrations |
| `backend/tests/` | API and model checks |
| `challenges/` | Validated public challenge records and starter code |
| `.github/workflows/` | CI with PostgreSQL and Chromium |

The initial migration creates `problems` and `starter_code`. Each problem uses one of six formats. Starter code is stored per problem and language. PostgreSQL is the runtime database, and the fast API/model suite uses isolated SQLite databases. Migration checks and browser integration use PostgreSQL.

### API

| Method and route | Purpose |
|---|---|
| `GET /api/v1/health` | Process liveness |
| `GET /api/v1/problems` | Catalog list with `q`, `category`, `difficulty`, `topic`, `limit`, and `offset` |
| `GET /api/v1/problems/{slug}` | Public description, constraints, examples, choices and starters |

## Checks

Keep the seeded backend running for the browser suite. Run these commands from the repository root with the Python environment activated.

```sh
(cd backend && pytest && alembic check)
cd frontend
npm ci
npm run typecheck
npm run build
npx playwright install chromium
npm test
```

Run migration upgrade/downgrade checks against a disposable database. A downgrade to base drops the catalog tables.
