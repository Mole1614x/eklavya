# Phase 15 performance and scalability report

Date: 2026-11-20  
Branch: `feature/phase-15-performance-scalability`  
Baseline: Phase 14 at `9b8d39e`

## Test environment and guardrails

Measurements ran on the managed single-host Linux workspace using one Uvicorn process, PostgreSQL 17 Alpine, Redis 7 Alpine, and at most two Celery judge processes. HTTP runs were bounded to 3,000 requests at concurrency 25. Locust ran for 20 seconds with 10 users. Judge batches were capped at four submissions. Databases and the load Redis instance were disposable. No production system or paid service was used.

Acceptance guardrails for this host were defined before the final run: mixed public reads at least 250 requests/second, p95 below 200 ms, p99 below 300 ms, under one percent errors; the mixed authenticated Locust journey required zero request errors and p95 below 250 ms. These figures describe this workspace only and are not a production capacity promise.

## Baseline and optimized HTTP results

The deterministic benchmark rotates through liveness, catalog, problem detail, leaderboard, contest list, and learning paths.

| Metric | Phase 14 baseline | Phase 15 | Change |
| --- | ---: | ---: | ---: |
| Requests | 3,000 | 3,000 | — |
| Concurrency | 25 | 25 | — |
| Requests/second | 262.83 | 422.49 | +60.7% |
| Median | 89.41 ms | 40.22 ms | -55.0% |
| P95 | 169.70 ms | 156.73 ms | -7.6% |
| P99 | 231.30 ms | 240.09 ms | +3.8% |
| Error rate | 0% | 0% | unchanged |

The p99 movement is reported as a small tail regression, not hidden by the stronger throughput/median result. It remains inside the 300 ms guardrail. Longer staging runs with production-like network and storage are required before choosing autoscaling thresholds.

## Locust user journeys

Locust 2.32.10 exercised cached/uncached browsing, problem retrieval, leaderboards, contest standings, registration, authenticated history, submission creation, and submission polling.

- 10 users, 2 users/second spawn rate, 20 seconds.
- 294 requests, 14.88 requests/second under user think-time.
- Median 4 ms, p95 11 ms, p99 52 ms, maximum 184 ms.
- 0 failed requests.
- Two password-hashed registrations completed; nine submissions were created and polled.
- Uvicorn used about 98 MiB RSS. A point-in-time CPU sample showed API 5.2%, PostgreSQL 23.1%, and Redis 11.8%; Redis reported 1.27 MiB logical memory. Point samples are diagnostic, not capacity guarantees.

Reproducible workloads are in `performance/benchmark.py`, `performance/locustfile.py`, and `performance/queue_benchmark.py`. Each refuses an unbounded local workload.

## Database review

Migration `0011_performance_reliability` adds composite indexes for catalog filters, submission lifecycle/history, active users, leaderboard order, rank history, and learning-path enrollment. Submission history and leaderboard now have bounded offset pagination. Connection-pool size, overflow, and timeout are explicit settings.

Plans were captured on a disposable database with 10,000 users and 105,000 submissions:

- A 25-row history page for a learner with 5,010 submissions used a backward `ix_submissions_user_created_at` scan: 0.080 ms, six shared-buffer hits.
- The 50-row leaderboard used the XP index with an incremental sort: 0.511 ms.
- Stuck-task detection used an index-only lifecycle scan: 0.030 ms, zero heap fetches.
- The 20-row catalog correctly chose a sequential scan in 0.027 ms; at this cardinality an index scan would be unnecessary. The composite catalog index becomes useful as the catalog grows.

Admin contest, path, and achievement lists were changed from per-row count queries to single correlated aggregate statements, removing those N+1 patterns.

## Cache and API behavior

Only public, identical-across-users data is cached: catalog pages, problem details, leaderboards, contest lists/standings, and learning-path lists. A one-second per-process L1 reduces Redis round trips; Redis holds the 30-second shared value. Administrative mutations and verified progression invalidate relevant namespaces. Cache failure falls back to PostgreSQL; no profile, submission source, token, private test, or hidden dataset is cached.

Submission history gained offset pagination. Leaderboard positions remain correct across offsets. The API metrics endpoint now reports lifecycle counts plus recent queue/execution duration and remains available if the submission metrics query temporarily fails.

## Queue and judge reliability

Delivered controls:

- late acknowledgements, lost-worker rejection, prefetch one, and bounded retries;
- a database lease with attempt count and stale-running reclamation;
- queued cancellation and cooperative running cancellation;
- an audited administrator recovery action for stale jobs;
- duplicate finalization and XP idempotency;
- queue wait, execution duration, status, cancellation, and stuck-task metrics.

A two-worker live batch uncovered a same-user XP finalization deadlock. The fix establishes a user-before-submission lock order and rolls back failed transactions before retry or terminal error handling. After the fix, four concurrent Python submissions all finished `ACCEPTED`; the retry path reclaimed one transient attempt without duplicate reward finalization.

Bounded isolated batches on the available images produced:

| Workload | Count | Result | Queue median / p95 | Execution median | Throughput |
| --- | ---: | --- | --- | ---: | ---: |
| Python | 4 | 4 Accepted | 2,889 / 4,157 ms* | 1,244 ms | 0.865/s |
| C | 2 | 2 Accepted | 166 / 166 ms | 1,774 ms | 0.962/s |
| C++ | 2 | 2 Accepted | 132 / 135 ms | 2,747 ms | 0.668/s |

\*The Python batch intentionally included recovered backlog/retry work; it is reliability evidence, not a clean latency baseline.

## Restart and outage verification

- PostgreSQL was restarted; readiness returned and all 20 seeded problems remained.
- Redis was restarted with a queued judge task; the queue still contained one task afterward.
- A worker started after that restart, consumed the retained task, and persisted `FINISHED|ACCEPTED|1`; queue depth returned to zero.
- Uvicorn was stopped and started; readiness returned both times and the catalog remained at 20 problems.
- Automated tests cover duplicate delivery, reward idempotency, stale lease recovery, queued cancellation, suspension, and cache-independent authorization.
- Redis loss degrades public caching to PostgreSQL. Production rate limiting continues to fail closed when its Redis protection store is unavailable.

## Frontend

Monaco is now a client-only dynamic chunk and initializes only inside a code workspace. Polling backs off from 500 ms to two seconds, accepts cancellation as terminal, and exposes a cancellation control. Problem lists remain server-paginated at 50 records. The responsive admin and learner routes passed TypeScript, production build, and Chromium journeys.

## Final verification

- Backend and judge regression suite: 45 passed (one upstream dependency warning).
- Alembic upgrade/check/downgrade/re-upgrade cycle: passed; final `alembic check` reported no pending operations.
- Frontend TypeScript and optimized production build: passed.
- Playwright Chromium journeys: 6 passed.
- Compose configuration rendering, Python workload-script compilation, and `git diff --check`: passed.

## Limitations

- The 7.9 GB sandbox could not keep PostgreSQL, build tooling, all scientific images, and the Java/PySpark images unpacked together. Java execution passed Phase 13, but Phase 15 concurrent Java measurement was blocked by local storage and is not reported as passed. PySpark, Pandas/NumPy, and ML concurrency measurements were likewise not repeated in this bounded phase; their functional evaluator checks remain covered by Phase 13 and automated contracts.
- TensorFlow remains unimplemented.
- The benchmark is a single-host short run. Multi-node saturation, network partitions, horizontal cache behavior, and hour-scale soak testing require staging capacity.
- Cancellation is cooperative once an isolated case is running; the current case remains bounded by the sandbox timeout before cancellation is observed.

## Status

Phase 15 acceptance criteria are met for the available environment: representative load tests ran with no HTTP errors, the discovered integrity deadlock was fixed and reverified, important plans and N+1 queries were reviewed, queue/Redis/worker recovery was verified, frontend optimization builds, and measured capacity plus blocked heavy-runtime limits are documented without unsupported scalability claims.
