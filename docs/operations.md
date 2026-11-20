# Production operations

## Pre-deployment checklist

1. Set unique PostgreSQL credentials, a random `SECRET_KEY` of at least 32 characters, the external `PRODUCTION_DATABASE_URL`, explicit origins/hosts, and `COOKIE_SECURE=true` in a secret store.
2. Place a TLS-terminating load balancer or host proxy in front of the loopback-only Nginx listener.
3. Build and scan the application and four allowlisted runner images. Do not permit learner-selected image names.
4. Capture a PostgreSQL backup and verify that it can be restored to a disposable instance.
5. Run `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile judge config` and review the resolved image, volume, port, and secret configuration.

## Deployment

The `migrate` service is a one-shot release task. It upgrades the schema and idempotently loads configuration records before API and judge services start.

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile judge build
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile judge up -d --wait
```

Check the release through the TLS endpoint:

```sh
curl --fail https://YOUR_HOST/api/v1/health/ready
curl --fail https://YOUR_HOST/api/v1/problems?limit=1
```

`/health/live` confirms the process can respond. `/health/ready` verifies PostgreSQL and, in production, Redis. Remove a replica from traffic whenever readiness fails. `/api/v1/metrics` exposes aggregate request, 5xx, duration, submission-state, queue-wait, and execution-duration metrics for scraping.

## Scaling and queues

API replicas are stateless. Rate limits and the Celery broker are shared in Redis; account and progression state is in PostgreSQL. Judge workers can scale independently, but each worker needs Docker access and should run only on dedicated sandbox hosts. Keep concurrency aligned with host CPU/memory and the per-container limits.

Monitor queue depth, oldest queued submission, judge task failures, API 5xx rate, database connections, Redis memory, disk space, and PostgreSQL backup age. Alert on repeated `SYSTEM_ERROR` verdicts and readiness failures.

Submission tasks use late acknowledgement and a database lease. Duplicate delivery is safe: terminal submissions are ignored and XP sources are unique. A running lease older than `JUDGE_STUCK_SECONDS` may be reclaimed. Administrators can review the stuck count and invoke the audited recovery action from `/admin`; do this only after confirming the original worker is unavailable. Learners can cancel queued work immediately and running work cooperatively between bounded test cases.

Public catalog, problem, contest, learning-path, and leaderboard data uses a short Redis cache with a one-second worker-local layer. Mutations invalidate their namespace. Private/user-specific responses are never shared. Cache failure falls back to PostgreSQL, so size the database for correctness without Redis cache hits.

Tune `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW` per API replica so the total across replicas remains below the PostgreSQL connection budget. Keep judge pools smaller than API pools. Do not raise Celery concurrency above the host's ability to sustain the per-container CPU and memory limits.

## Backup and recovery

Back up PostgreSQL with the platform's managed snapshot facility or `pg_dump --format=custom`. Redis contains queues and transient rate counters; PostgreSQL remains the source of truth. Restore into an isolated environment, apply the same application version, run `alembic current`, and perform API/browser smoke tests before directing traffic.

Schema downgrades are tested for development safety, but production rollback should normally restore the pre-release database snapshot and previous images. Never downgrade a live database after new-version writes without reviewing migration data loss.

## Email integration

The API persists only account-token digests. Add a transactional email adapter that receives the opaque token at issuance, renders a link rooted at `PUBLIC_URL`, and sends it without logging the token. Configure provider credentials through the secret store and redact provider payloads from tracing.
