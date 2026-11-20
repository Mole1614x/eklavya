# Database and migrations

PostgreSQL 17 is the production source of truth. SQLAlchemy owns runtime access and Alembic owns every schema change. SQLite is used only by narrow automated evaluator and unit-test fixtures.

## Data domains

- Identity: users, profiles, hashed refresh/account tokens.
- Curriculum: problems, starter code, test cases, evaluator contracts.
- Evaluation: submissions and contest submissions.
- Progression: XP transactions, ranks/history, achievements, daily activity, learning paths/progress.
- Competition: contests, assigned problems, registrations, standings inputs, ratings.
- Administration: managed dataset metadata and append-only audit logs.

Foreign keys, unique XP sources, terminal submission guards, and row locks protect progression from duplicate Celery delivery. Finalization locks the user before the submission to maintain one global lock order.

## Migration procedure

Never let every API replica race migrations. Run the one-shot `migrate` service once for the release, then start application replicas:

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --wait
```

Before review, verify on a disposable database:

```sh
cd backend
alembic upgrade head
alembic check
alembic downgrade base
alembic upgrade head
```

Downgrade coverage proves migration mechanics; it is not permission to downgrade a live database after new-version writes. Restore the pre-release snapshot and previous images for a data-safe production rollback.

## Backup

`scripts/backup_postgres.sh` creates a permission-restricted custom-format archive, verifies its table of contents, writes SHA-256 evidence, and removes archives older than `BACKUP_RETENTION_DAYS`. `scripts/restore_postgres.sh` refuses the configured production URL and requires a target database ending in `_restore_test` plus an explicit confirmation value. See [deployment](deployment.md) for the rehearsal sequence.
