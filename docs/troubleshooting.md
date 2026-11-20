# Troubleshooting

## Readiness returns 503

Check `X-Request-ID`, API logs, PostgreSQL readiness, then authenticated Redis. Production readiness intentionally fails if either dependency is unavailable. Do not remove Redis from readiness while production rate limits fail closed.

## Login or mutation returns 403

Confirm the public URL, `Host`, `Origin`, TLS edge, and forwarded host/protocol. Unsafe browser BFF routes reject `Sec-Fetch-Site: cross-site` and mismatched origins. Confirm `ALLOWED_ORIGINS` contains only the exact HTTPS browser origin and `ALLOWED_HOSTS` includes the public host and internal `backend` name.

## Mutation returns 429 or protection 503

Inspect Redis reachability, password consistency between `REDIS_PASSWORD` and `PRODUCTION_REDIS_URL`, and rate-limit keys. A 503 during Redis loss is the expected fail-closed behavior for protected production mutations.

## Submission stays queued

Check queue age and depth, Redis AOF health, Celery worker heartbeats/logs, runner image availability, Docker disk, and socket permissions. Do not recover a lease until the original worker is confirmed unavailable. Use the audited admin recovery action for work older than `JUDGE_STUCK_SECONDS`.

## Submission returns `SYSTEM_ERROR`

Correlate the submission time with worker logs and `eklavya_judge_system_errors_15m`. Verify the allowlisted runtime image exists locally; workers use `--pull never`. Inspect disk, Docker daemon health, dataset mounts, and database connectivity. Never reclassify a platform error as learner failure or acceptance.

## Database connections exhausted

Multiply `DATABASE_POOL_SIZE + DATABASE_MAX_OVERFLOW` by the number of API replicas and add judge/migration/operator connections. Lower per-process budgets or increase the reviewed PostgreSQL limit; do not hide exhaustion with unbounded pools.

## Restore script refuses the target

This is a safety control. Use a separately created database whose name ends in `_restore_test`, set the explicit confirmation value, and ensure `RESTORE_DATABASE_URL` is not equal to `PRODUCTION_DATABASE_URL`. Never weaken the guard to test against production.

## TLS/container start failure

Validate Compose with the exact override set. For direct TLS, ensure the certificate/key paths exist on the host and are readable by the container. Prefer the default loopback edge behind a managed TLS load balancer if certificate lifecycle cannot be automated safely.
