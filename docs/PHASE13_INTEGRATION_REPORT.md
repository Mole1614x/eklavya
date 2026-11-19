# Phase 13 integration report

Date: 2026-11-19  
Branch: `feature/phase-13-integration-testing`  
Baseline: Phase 12 PR #12 at `2eaba52` (open, green, mergeable, no conflicts)

## Test environment

- Managed Linux workspace with Docker Engine and 7.9 GB writable storage.
- PostgreSQL 17 Alpine and Redis 7 Alpine from the project Compose file.
- FastAPI/Uvicorn on a loopback test port, Next.js standalone server, and a Celery solo worker.
- Disposable Redis on `127.0.0.1:6380` for the host-launched end-to-end worker; the normal Compose Redis remained private and its persistent data was not modified.
- Isolated Docker runners with networking disabled, read-only root filesystems, dropped capabilities, PID/CPU/memory/output/time limits, and ephemeral tmpfs workspaces.

## Automated results

| Check | Result | Evidence |
| --- | --- | --- |
| Backend and judge tests | Passed | 37 passed; one upstream Starlette/httpx deprecation warning |
| Frontend type generation and TypeScript | Passed | `npm run typecheck` |
| Frontend production build | Passed | `npm run build`; all routes compiled |
| Browser journeys | Passed | 6 Playwright tests |
| Alembic consistency | Passed | upgrade, `alembic check`, downgrade to base, re-upgrade on a disposable database |
| Compose validation | Passed | `docker compose config --quiet` |
| Runner Dockerfile validation | Passed | BuildKit checks for code, data, big-data, ML, and deep-learning runners |
| Backup and restore | Passed | `pg_dump` restored into a disposable database; all 20 problems verified; database removed |

## Live integration results

The following checks used real services and evaluators rather than mocked HTTP responses.

- Registration, HttpOnly session creation, access-cookie removal, refresh-token rotation, authenticated submission creation, profile update, logout, refresh, and protected-route redirect passed in Chromium.
- The complete submission lifecycle passed: FastAPI → PostgreSQL → Redis → Celery → isolated Python runner → PostgreSQL result → API polling. The final result was `ACCEPTED`, 2/2 tests, source was not exposed, and authoritative XP/progress was awarded once.
- A `RUN` used only the public case and passed 1/1. The same incorrect solution submitted against hidden cases returned `WRONG_ANSWER`, 1/2, and concealed the hidden expected output.
- An invalid C submission returned `COMPILATION_ERROR` and received no completion reward.
- Correct console programs ran successfully in isolated Python, C, C++, and Java containers.
- A Python infinite loop returned `TIME_LIMIT_EXCEEDED`; a thrown exception returned `RUNTIME_ERROR`; invalid C returned `COMPILATION_ERROR`.
- SQL aggregation returned the expected ordered result. A `DELETE` statement was rejected by the SQLite authorizer.
- Pandas expression mode, Pandas full-program mode, NumPy expression mode, and MapReduce function mode produced their expected structured results.
- NumPy/scikit-learn AI function evaluation produced correct linear predictions and F1 output with configured tolerance handling.
- Daily Sadhana idempotency/streak, learning path progress, gamification idempotency/ranks, contest timing/registration/standings/ratings, and submission ownership were exercised by the automated backend suite.

## Defects discovered and fixed

1. Refresh cookies were scoped to `/api/auth`, so an expired access token could not be rotated by submission, contest, learning, or gamification BFF routes. A shared refresh-and-retry layer now covers every authenticated BFF route and rotates one-time refresh tokens.
2. Rootless Docker could not traverse worker-created `0700` temporary directories or read `0600` source files. Ephemeral staging is now container-readable and remains read-only inside the runner.
3. Docker stdin was not attached, causing `input()`, `scanf`, `cin`, and `Scanner` to receive EOF. Runners now use interactive stdin.
4. The compiler work tmpfs was not writable by the non-root runner user. Runner tmpfs mounts now use explicit mode `1777` while retaining size, execution, and nosuid restrictions.
5. A login shell reset the Java image PATH, hiding `javac`. The runner now uses the image's normal environment.
6. Missing images were pulled inside a graded execution and the pull time was reported as a user timeout. Grading uses `--pull never`; missing preprovisioned runtimes return a platform `SYSTEM_ERROR`.
7. The general-purpose GCC image was too large for a bounded worker. C/C++ now use a dedicated 233 MiB Alpine toolchain image provisioned by Compose.
8. Cold scientific imports could complete correctly at the timeout boundary and still be marked as timed out during container teardown. A bounded two-second platform-overhead allowance is separate from the five-second user budget.
9. Runner builds did not support private/corporate build CAs. All runner Dockerfiles now accept the same optional BuildKit `build_ca` secret without retaining it in the final image.
10. MapReduce unnecessarily required the PySpark image. It now runs in the minimal isolated Python runtime; Spark still uses the dedicated Spark runner.

## Security verification

Passed:

- Public registration cannot select the administrator role.
- Malformed and expired JWTs are rejected.
- A token with a forged `role=admin` claim cannot override the role stored in PostgreSQL.
- Deactivated accounts cannot continue using an existing access token.
- Cross-user submission access returns 404 and submission source is absent from API schemas.
- Refresh tokens are one-time, rotated, revoked on logout, and revoked after password reset.
- Hidden expected output remains concealed after a failed hidden test.
- SQL mutation, attach, pragma, and schema-changing operations remain denied.
- Untrusted execution has no network, a read-only root filesystem, dropped capabilities, no-new-privileges, and bounded resources.

## Blocked or deferred checks

| Check | Status | Reason |
| --- | --- | --- |
| Live PySpark container execution | Blocked locally | The managed workspace cannot hold the Spark image alongside all verification images. MapReduce ran live and the PySpark runner contract passed automated tests. Hosted/staging capacity is required. |
| Live PyTorch container execution | Blocked locally | The CPU PyTorch image exceeds remaining workspace storage. Tensor shape/dtype contracts passed automated tests. |
| TensorFlow execution | Not tested | No TensorFlow evaluator or catalog challenge exists in the current product; this is not reported as implemented. |
| Transactional email delivery | Blocked | Verification/reset token architecture exists, but no email provider is configured. Tokens are never logged. |
| Large concurrent load and restart/failover matrix | Deferred | Covered by Phase 15 in a bounded disposable environment. |

## Integration status

Phase 13 acceptance criteria are met for the available environment: critical tests, production frontend build, authenticated browser workflow, real code execution, representative data/AI evaluation, complete submission lifecycle, rankings/progress consistency, security controls, migrations, and disposable backup/restore all passed. The unavailable heavy runtimes are explicitly blocked rather than represented as successful.
