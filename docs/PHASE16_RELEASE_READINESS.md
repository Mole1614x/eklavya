# Phase 16 release readiness

Date: 2026-11-20

Branch: `feature/phase-16-production-readiness`

Release candidate: `1.0.0`

Baseline: Phase 15 at `e108302`

## Delivered release controls

- A documented production topology for Next.js, FastAPI/Uvicorn, PostgreSQL, authenticated Redis, Celery, isolated judge workers, private dataset storage, a reverse proxy, HTTPS, and private monitoring.
- A non-secret `.env.production.example` plus production validation that rejects non-PostgreSQL databases, unauthenticated/non-Redis brokers, non-HTTPS public URL/origins, weak signing secrets, wildcard hosts/origins, and disabled rate-limit/readiness controls.
- Production Compose network segmentation, resource/PID caps, bounded JSON logs, private service ports, authenticated Redis, health checks, restart policies, non-root/read-only application services, an optional direct-TLS override, and an optional private Prometheus service.
- Cookie-BFF CSRF defense using SameSite cookies plus `Origin`/Fetch Metadata rejection on every unsafe browser route.
- Private Prometheus metrics and rules for API/database availability, stuck judge work, oldest queue age, recent judge system errors, and API error rate. Public Nginx returns 404 for metrics.
- Guarded PostgreSQL backup and restore scripts with custom archives, SHA-256 verification, retention, explicit disposable-target naming, and a production-URL refusal.
- CI preparation for Python/npm dependency audits, migrations, backend/judge tests, TypeScript, optimized frontend build, seven real browser journeys, all Dockerfile checks, production/TLS/monitoring Compose rendering, Nginx syntax, Prometheus rules, and core-stack smoke testing. There is no deployment job.
- Version `1.0.0`, changelog, architecture/API/database/judge/security/deployment/troubleshooting documentation, release sequence, incident response, secret rotation, and data-safe rollback procedure.

## Verification matrix

| Check | Status | Evidence |
| --- | --- | --- |
| Backend and judge regression | Passed | 51 tests; one upstream Starlette/httpx deprecation warning |
| Security cases | Passed | forged/expired tokens, database role, inactive user, ownership, CORS, SQL syntax as data, upload restrictions, headers/hosts, isolation, CSRF |
| Alembic consistency | Passed | `alembic check`: no new operations; Phase 15 disposable upgrade/downgrade/re-upgrade remains valid because Phase 16 has no model change |
| Production settings validation | Passed | valid PostgreSQL/authenticated-Redis/HTTPS configuration imported; insecure variants rejected by tests |
| Frontend TypeScript | Passed | `npm run typecheck` and build-integrated TypeScript |
| Frontend production build | Passed | Next.js 16.4.6 optimized build; all routes compiled |
| Browser/UAT flows | Passed | 7 Playwright Chromium tests against real Next/Uvicorn/PostgreSQL services |
| Dependency advisories | Passed | npm production audit: 0; pip-audit: no known vulnerabilities |
| Backup/restore | Passed | database archived, portable checksum verified, restored all 21 current problem rows (20 seeds plus the archived UAT artifact) into `eklavya_restore_test`; production-target refusal passed; disposable data removed |
| Compose definitions | Passed | base, production, direct-TLS, and monitoring combinations rendered successfully |
| Dockerfile static checks | Passed | backend, frontend, judge, code, data, big-data, ML, and deep-learning definitions |
| Shell/patch hygiene | Passed | backup/restore `bash -n`; `git diff --check` |
| Nginx/Prometheus container syntax | Not tested locally | Images could not be unpacked alongside the 7.9 GB workspace; deterministic checks are in CI |
| Full production-profile startup | Blocked locally | Authenticated Redis, proxy, monitoring, and all runner images exceed local storage together; staging is the required gate |
| Direct TLS handshake/certificate renewal | Not tested | Requires operator-owned DNS/certificates or managed load balancer |

## Final user acceptance journeys

Evidence combines the current seven-browser suite and the real-service Phase 13 evaluator runs. No mock HTTP success response is counted.

| Journey | Status | Evidence/limit |
| --- | --- | --- |
| Beginner programmer | Passed | Real registration/session, Foundations/Monaco navigation, isolated Python submission, verified result and one-time XP evidence |
| DSA learner | Passed | DSA catalog/workspace, isolated Python execution, result/history/progression contracts |
| Data analyst | Passed | Live SQL aggregation, Pandas expression/program, NumPy, and current Statistics UI/evaluator evidence |
| Data engineer | Blocked | MapReduce ran live; PySpark contract passed, but the Spark image could not fit on this host |
| ML engineer | Passed | Live scikit-learn/NumPy AI-function evaluation with structured tolerance feedback |
| Competitive programmer | Passed | Real Arena browser discovery plus registration, scoped submissions, standings, penalty, rating, and finalization integration tests |
| Administrator | Passed | Current real BFF journey: login, create a problem with public/hidden cases, publish it, review contest submissions, archive it |
| Daily learner | Passed | Daily discovery/navigation plus verified completion, one-time XP, and streak integration evidence |

PyTorch evaluator contracts passed automated tests but the CPU image was storage-blocked for the final live rerun. TensorFlow is not implemented and is not represented as a passed ML/AI capability.

## Release decision

The code is development-ready, integration-tested, and staging-ready. It is not production-deployed. Declare it production-ready only after a production-sized staging environment passes the full production profile, PySpark/PyTorch runtime smoke tests, direct or managed TLS validation, alert delivery, external backup retention, email-provider integration decision, and an independent security review appropriate to the intended threat level.

No public deployment, paid infrastructure, branch merge, or production data change is authorized by this report.
