# Phase 14 administration report

Date: 2026-11-19  
Branch: `feature/phase-14-admin-dashboard`  
Baseline: Phase 13 branch at `56ee58c`

## Delivered controls

- A protected, connected `/admin` control center with operational totals, submission trends, queue counts, recent registrations, and responsive tables.
- Server-side administrator authorization on every administrative API. Public registration still accepts no role field, and administrator provisioning is a trusted CLI operation.
- Problem create/edit, lifecycle controls, starter code, public/private tests, evaluators, all six challenge formats, and published-problem preview.
- Validated private CSV, JSON, and Parquet uploads with a five MiB default limit, SHA-256 metadata, restrictive file permissions, versioning, activation controls, and administrator-only download.
- User search, profile/status review, submission summaries, system-error signals, suspension/reactivation, and self-suspension prevention. Passwords and authentication tokens are absent from every admin schema.
- Contest create/edit/schedule/problem assignment/scoring/publication/cancellation plus registration, standings, and submission review. Finalized or rated results are immutable through CRUD; only the verified finalization workflow may finalize a contest.
- Learning-path prerequisites, milestones, problem assignment, publication, and archival state.
- Achievement definitions with allowlisted criteria, read-only XP transactions, and read-only rank progression. There is no arbitrary XP mutation endpoint.
- Append-only administrative audit records containing actor, action, target, bounded context, IP address, and time.

## Security model

The browser talks to a same-origin Next.js BFF route. Access and rotating refresh tokens remain HttpOnly cookies. The FastAPI dependency reloads the user and role from the database, so a forged role claim cannot grant administrator access. File names cannot contain paths; accepted file formats are parsed or signature-checked before storage. Pagination is bounded to 100 records for general lists and 500 records for a single contest review.

Administrator accounts are provisioned without exposing a public role selector:

```sh
export EKLAVYA_ADMIN_PASSWORD='use-a-secret-input-mechanism-in-production'
PYTHONPATH=. python -m backend.app.provision_admin --email admin@example.com --username admin --display-name "Platform Administrator"
unset EKLAVYA_ADMIN_PASSWORD
```

Omit `EKLAVYA_ADMIN_PASSWORD` for an interactive, non-echoed prompt. In production, inject it from the approved secret manager and avoid shell history.

## Verification

| Check | Result |
| --- | --- |
| Backend and judge tests | Passed: 41 tests after the admin API additions |
| Authorization tests | Passed: learner denied, database-backed admin accepted, suspended session rejected, self-lockout prevented |
| Problem lifecycle and public visibility | Passed: draft hidden, publish visible, archive hidden, audit records written |
| Dataset controls | Passed: validation, versioning, private download, deactivation, and path traversal rejection |
| Contest/path/achievement controls | Passed, including finalized-result edit lock and contest operations review APIs |
| Alembic | Passed on a disposable PostgreSQL database: upgrade, check, downgrade one revision, re-upgrade |
| Frontend TypeScript | Passed |
| Frontend production build | Passed; `/admin` and the authenticated admin proxy compiled |
| Browser authorization journey | Passed: learner receives a clear restricted-area state |

## Operational limitations

- Dataset files use a private mounted volume for the single-host topology. Multi-host deployments should replace this with private object storage and short-lived administrator downloads.
- Administrative tables are intentionally bounded. A future high-volume installation should add cursor pagination and export jobs rather than increasing response limits.
- Audit logs are application append-only, not tamper-proof. Production should export them to retained centralized logging with access controls.
- The dashboard highlights system errors as a suspicious-activity signal; automated abuse scoring is not claimed.

## Status

Phase 14 acceptance criteria are met: administrator authentication and login sessions work, non-administrators are denied, content/dataset/user/contest/path/achievement operations are connected to validated APIs, actions are audited, migrations are reversible, and the relevant test/build/browser checks pass.
