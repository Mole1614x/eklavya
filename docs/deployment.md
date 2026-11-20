# Production deployment and rollback

The repository is prepared for a reviewed single-host or staging release. It does not authorize a public deployment.

## Prerequisites

- Patched Linux host, Docker Engine, Compose v2 with `!override` support, DNS, and either a managed HTTPS load balancer or operator-owned certificate/key files.
- PostgreSQL/Redis capacity and a dedicated Docker worker host for public untrusted execution.
- Secret manager values for PostgreSQL, authenticated Redis, a 32+ character signing key, explicit HTTPS origin/URL, and trusted hosts.
- Central log retention, alert routing, backup storage, and a transactional email provider if verification/reset delivery is required.

Copy `.env.production.example` outside the repository, restrict it to the operator, and fill every blank value. `PRODUCTION_DATABASE_URL` uses SQLAlchemy's `postgresql+psycopg://` form. `PRODUCTION_REDIS_URL` must contain the percent-encoded `REDIS_PASSWORD`.

## Review configuration

```sh
docker compose --env-file /secure/path/eklavya.env \
  -f docker-compose.yml -f docker-compose.prod.yml --profile judge config
```

The default production edge is loopback HTTP for a managed TLS terminator. For direct TLS, add `-f docker-compose.tls.yml`; that override publishes 443 and mounts the configured certificate/key read-only. Never expose the loopback HTTP topology as public plaintext.

## Release sequence

1. Confirm CI, release version/changelog, open risks, and reviewer approval.
2. Back up PostgreSQL and successfully restore the archive into a disposable `*_restore_test` database.
3. Build and scan immutable application and runner images. Record their digests.
4. Put the release into maintenance/drain mode at the external edge if migrations require it.
5. Run the one-shot migration service.
6. Start database/Redis, API/frontend, proxy, then profile-gated judge workers. Wait for readiness.
7. Execute learner and administrator smoke journeys through HTTPS; inspect queue, database, error, and worker metrics.
8. Re-enable traffic gradually and retain the rollback snapshot until the observation window closes.

```sh
docker compose --env-file /secure/path/eklavya.env \
  -f docker-compose.yml -f docker-compose.prod.yml --profile judge build
docker compose --env-file /secure/path/eklavya.env \
  -f docker-compose.yml -f docker-compose.prod.yml run --rm migrate
docker compose --env-file /secure/path/eklavya.env \
  -f docker-compose.yml -f docker-compose.prod.yml --profile judge up -d --wait
```

Optional private Prometheus:

```sh
docker compose --env-file /secure/path/eklavya.env \
  -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.monitoring.yml \
  --profile monitoring up -d prometheus
```

## Backup rehearsal

```sh
DATABASE_URL='postgresql://...' BACKUP_DIR=/secure/backups \
  scripts/backup_postgres.sh

RESTORE_DATABASE_URL='postgresql://.../eklavya_restore_test' \
BACKUP_FILE=/secure/backups/eklavya-YYYYMMDDTHHMMSSZ.dump \
EKLAVYA_CONFIRM_RESTORE=RESTORE_DISPOSABLE_ONLY \
PRODUCTION_DATABASE_URL='postgresql://.../eklavya' \
  scripts/restore_postgres.sh
```

Retain daily encrypted database backups for the policy period (14 days by default), maintain longer weekly/monthly snapshots according to legal requirements, and test one restore at least monthly. Dataset objects require a separate encrypted/versioned backup policy. Redis is not the system of record, but AOF protects accepted queue entries during ordinary restarts.

## Rollback

Stop promotion if readiness, migrations, authentication, a representative submission, or admin authorization fails. Before any incompatible writes, roll back by stopping new services and starting the recorded previous image digests. After incompatible writes, do not run an Alembic downgrade blindly: stop traffic/workers, preserve incident evidence, restore the pre-release PostgreSQL snapshot into a new database, point the previous release at it, verify counts and smoke journeys, then switch traffic. Record the timeline and reconcile any submissions accepted after the snapshot before reopening.

Rotate signing, database, Redis, TLS, and provider secrets independently through the secret manager. Signing-key rotation invalidates current JWTs; plan a user sign-in window. For an incident: contain traffic and judge workers, preserve logs/audit records, rotate affected credentials, restore/repair from verified evidence, validate in isolation, communicate scope, and write a post-incident review.
