# API guide

All backend routes are under `/api/v1`. Production OpenAPI and ReDoc pages are disabled; generate or inspect the schema in a controlled non-production environment.

## Conventions

- JSON requests use explicit Pydantic schemas. Unknown registration fields, including `role`, are rejected.
- Bearer access tokens expire after 15 minutes by default. Refresh tokens are opaque, stored only as digests, rotated once, and revoked by logout or password reset.
- Browser clients use same-origin `/api/*` Next.js BFF routes and HttpOnly cookies. Direct API clients send `Authorization: Bearer <access token>`.
- Collection limits are bounded. Submission history and leaderboards accept `limit` and `offset`; admin collections cap their page size.
- Errors use `{"detail": ...}`. Operational 503 responses and normal API responses include `X-Request-ID` for log correlation.
- Submission source, hidden expected output, password data, account-token digests, and private dataset paths are never returned by public schemas.

## Route groups

| Area | Representative routes |
| --- | --- |
| Health/metrics | `GET /health/live`, `/health/ready`, `/metrics` |
| Catalog | `GET /problems`, `/problems/{slug}` |
| Accounts | `POST /auth/register`, `/login`, `/refresh`, `/logout`, verification/reset; `GET/PATCH /auth/me` |
| Submissions | `POST /problems/{slug}/submissions`, `GET /submissions`, `GET /submissions/{id}`, `POST /submissions/{id}/cancel` |
| Progression | ranks, leaderboard, dashboard, achievements, and insights under `/gamification` |
| Learning | daily challenge/history/completion and Vidya Path list/detail/enrollment under `/learning` |
| Arena | contest discovery, registration, participant state, submissions, standings, ratings, and finalization under `/contests` |
| Administration | overview, recovery, content, private datasets, users, contests, paths, achievements, XP/ranks, and audit history under `/admin` |

`RUN` evaluates public cases only. `SUBMIT` evaluates the full public/private contract and is the only mode eligible for verified progression. Creation returns HTTP 202; clients poll the submission resource until `FINISHED`, `SYSTEM_ERROR`, or `CANCELLED`.

Administrative authorization is checked from the current database user on every request. A role claim in a token cannot promote an account.
