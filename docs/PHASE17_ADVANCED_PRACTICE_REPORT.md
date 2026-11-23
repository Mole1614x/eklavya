# Phase 17 — Advanced Practice Report

## Scope

Phase 17 integrates timed assessments, personal data cleaning, Excel and Tableau expression practice, Linux/Bash execution, multi-tool challenges, interview templates, a dataset library, and skill analytics into the existing Next.js, FastAPI, PostgreSQL, Redis/Celery, and isolated-judge architecture.

The implementation is additive. Existing authentication, catalog, submissions, progression, learning paths, contests, administration, operational controls, and Windows startup behavior remain in place.

## Timed assessments

Administrators can:

- create or edit assessments from the existing problem bank;
- select coding, DSA, SQL, Pandas, statistics, data-engineering, Excel, Tableau, Linux, or mixed assessment types;
- configure the open/close window, duration, attempts, scoring, penalties, instructions, result release, and publication state;
- assign individual learners or reusable learner groups;
- instantiate role templates for Python Developer, Data Analyst, Data Engineer, ML Engineer, and Software Developer;
- review aggregate completion and score analytics;
- export attempt results as CSV or XLSX; and
- review all changes through the append-only administrative audit log.

Learners see only assigned, published assessments. Starting an assessment creates an attempt with a deadline equal to the earlier of the configured duration and assessment close time. All saves and submissions re-check the deadline on the server. Refreshing returns the existing active attempt and authoritative server time. Starting beyond the attempt limit is rejected.

Code, SQL, data, Excel, Tableau, and Bash answers can be submitted from the assessment to the existing judge. The attempt stores only the submission reference and uses the judge verdict when scoring. A manual finalization is idempotent and refuses to race queued/running judge work. The active browser requests finalization when its server-derived countdown reaches zero; independently, an expired attempt is finalized when the learner next accesses, saves, or submits it, and late work is never accepted.

## Data Cleaning Lab and dataset library

Supported uploads:

| Format | Preview reader |
|---|---|
| CSV | UTF-8, bounded standard CSV parser |
| XLSX | `openpyxl` in read-only/data-only mode |
| JSON | array of objects or `{ "rows": [...] }` |
| Parquet | bounded in-memory DuckDB reader |

The API enforces filename, MIME, encoded/decoded size, XLSX ZIP entry and decompressed-size limits, row, column, cell, per-user quota, and ownership controls. Profiles include dimensions, inferred types, missing counts, distinct counts, duplicate rows, numerical summaries, IQR outliers, bounded distributions, and pairwise numerical correlations. Previewing data never executes uploaded Python or workbook macros.

Supported structured transformations are duplicate removal, missing-row removal, missing-value fill, type conversion, min/max normalization, ISO date standardization, and column renaming. Cleaned CSV exports neutralize cells beginning with `=`, `+`, `-`, or `@` to prevent spreadsheet formula injection.

Free Pandas, NumPy, and SQL practice creates a queued `DatasetPracticeRun`. Celery copies only the authorized dataset into a disposable data-runner container. Submitted code never executes in FastAPI or the Celery worker process. Output is bounded and the sandbox is destroyed after each run.

Administrators can publish synthetic or appropriately licensed CSV, XLSX, JSON, and Parquet files into the versioned dataset library under Retail, Banking, E-commerce, Healthcare, Sales, HR Analytics, Finance, or Logistics categories. Published download permissions remain explicit. Private learner data is never published implicitly.

## Excel practice

The safe recursive-descent parser does not call Python `eval()`. It supports:

- arithmetic, comparisons, concatenation, finite cell/range references, and parentheses;
- `SUM`, `AVERAGE`, `MIN`, `MAX`, `COUNT`, `COUNTA`, and `IF`;
- `SUMIF`, `SUMIFS`, `COUNTIF`, `COUNTIFS`, `XLOOKUP`, `INDEX`, `MATCH`, and `IFERROR`;
- `ABS`, `ROUND`, `LEN`, `LEFT`, `RIGHT`, `MID`, `CONCAT`, `UPPER`, `LOWER`, and `TRIM`;
- `DATE`, `YEAR`, `MONTH`, `DAY`, `AND`, `OR`, and `NOT`.

Formula text submissions and XLSX uploads are supported. Workbook grading reads the configured answer cell and evaluates the formula against a server fixture. Hidden judge fixtures are stored separately from public challenge content. `VLOOKUP` and `HLOOKUP` that require two-dimensional workbook semantics are explicitly rejected by the text evaluator and should use an administrator-reviewed workbook challenge. The platform does not claim full Microsoft Excel compatibility.

## Tableau practice

The validator checks balanced syntax, allowed tokens, field references, and a documented function allowlist. The evaluator supports:

- `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, and `COUNTD` aggregates;
- arithmetic between aggregates;
- `{ FIXED [...] : aggregate(...) }` grouping semantics;
- `RUNNING_SUM`, `WINDOW_SUM`, and `WINDOW_AVG`; and
- explicit partition fields and an order field for table-calculation context.

Unsupported Tableau functions return an explicit error. INCLUDE/EXCLUDE, nested LOD, parameter behavior, and complex visualization filter-order semantics require administrator review until a complete semantic implementation is added. The platform does not claim a complete Tableau runtime.

## Linux and Bash

Linux is a first-class catalog category. Starter challenges cover recursive file discovery and deterministic log processing. Bash submissions run in a fresh Alpine container with:

- UID/GID `65534:65534`;
- no network;
- a read-only root filesystem;
- no privileged mode and all Linux capabilities dropped;
- `no-new-privileges`;
- bounded processes, CPU, memory, time, and output;
- read-only submission/fixture mounts and disposable writable tmpfs; and
- validated fixture paths that reject absolute paths and `..` traversal.

The sandbox is the same Docker-socket infrastructure boundary documented for the existing judge. A public hostile-code deployment should move the judge to a dedicated host or external sandbox service.

## Multi-tool challenges and analytics

The initial multi-tool challenge asks learners to calculate sales by region using SQL, Pandas, PySpark, Excel, or Tableau. Each technology has its own validation rules and independent completion record. Graders preserve differences in syntax and calculation context instead of treating superficially similar answers as equivalent.

Skill analytics aggregate authoritative submissions and completed assessments for the current learner only. The Progress Insights screen now displays live totals, subject mastery, recent activity, assessment completion, and weak subjects instead of demo analytics. Queries are grouped and bounded to the latest 30 active days.

## Database migration

Migration `0012_advanced_practice` creates:

- `assessments`, `assessment_questions`, `assessment_assignments`, and `assessment_group_assignments`;
- `learner_groups` and `learner_group_members`;
- `assessment_attempts`, `assessment_answers`, and `assessment_results`;
- `practice_datasets` and `dataset_practice_runs`; and
- `multi_tool_progress`.

The migration is reversible. It was verified on a disposable PostgreSQL 17 database with upgrade to head, `alembic check`, downgrade to the Phase 16 head, and re-upgrade to head.

## API endpoints

All paths are below `/api/v1/advanced`.

| Area | Endpoints |
|---|---|
| Templates/groups | `GET /templates`, `GET/POST /admin/groups` |
| Assessment administration | `GET/POST /admin/assessments`, `POST /admin/assessments/from-template/{key}`, `PUT /admin/assessments/{id}`, `PATCH .../status`, `GET .../analytics`, `GET .../export` |
| Learner assessments | `GET /assessments`, `POST /assessments/{id}/start`, `GET /assessments/attempts/{id}`, `PUT .../answers`, `POST .../questions/{slug}/submissions`, `POST .../submit` |
| Data Lab/library | `POST /datasets`, `GET /datasets/mine`, `GET /datasets/library`, `POST /datasets/{id}/transform`, `GET /datasets/{id}/download`, `DELETE /datasets/{id}` |
| Data Lab execution | `POST /datasets/{id}/practice`, `GET /datasets/practice/{run_id}` |
| Dataset administration | `GET /admin/datasets`, `PATCH /admin/datasets/{id}` |
| Expression practice | `POST /excel/evaluate`, `POST /excel/evaluate-workbook`, `POST /tableau/evaluate` |
| Multi-tool | `GET /multi-tool/challenges`, `POST /multi-tool/submit` |
| Analytics | `GET /analytics` |

The Next.js BFF mirrors these endpoints under `/api/advanced/*`, keeps access/refresh tokens in HTTP-only cookies, rotates sessions, and rejects cross-site mutations.

## Local setup

Use the full judge profile so code, Bash, Data Lab, Excel, and Tableau submissions execute:

```sh
cp .env.example .env
docker compose --profile judge up --build -d --wait
```

On Windows, double-click `start.bat`. The default command starts the complete judge profile. `start.bat web` intentionally omits working code execution.

## Verification evidence

Executed on the Phase 17 branch:

- backend regression and Phase 17 API/security tests: **44 passed**;
- judge isolation/evaluator/lifecycle tests: **16 passed**;
- frontend route generation and TypeScript typecheck: **passed**;
- Next.js optimized production build: **passed**;
- Playwright browser journeys using system Chromium: **8 passed**;
- PostgreSQL migration upgrade/check/downgrade/re-upgrade: **passed**;
- JSON challenge/evaluator fixture validation: **passed**.

## Known limitations

- Text formula grading intentionally supports finite ranges rather than entire-column references. Workbook-only functions and features such as Pivot Tables, Power Query, conditional formatting, dynamic arrays beyond the parser subset, and external links require structured answers or administrator review.
- Tableau INCLUDE/EXCLUDE, nested LOD, parameters, and advanced filter-order/addressing behavior are validated but not auto-graded unless they fall within the documented evaluator subset.
- Assessment expiration is enforced on every server interaction and is finalized on the next attempt access/save/submit. Deployments that require result rows to appear at the exact deadline without learner traffic should add a periodic Celery sweep.
- Uploaded dataset storage is a private local volume in the single-host Compose setup. Multi-host production requires private object storage, encryption/lifecycle policies, and an asynchronous object scanner.
- Docker-socket access remains a critical judge infrastructure boundary; the project has not received an independent penetration test.
