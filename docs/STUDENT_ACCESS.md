# EKLAVYA student access and publication

## Scope

Published and accessible are **independent** dimensions. Student targeting
is not the same as account-role authorization, contest registration,
assessment timing, or result release.

| Publication | Scope | Learner visibility |
|---|---|---|
| Draft/unpublished/private | ALL | Not visible |
| Draft/unpublished/private | SELECTED | Not visible |
| Published | ALL | Every eligible learner; no assignments required |
| Published | SELECTED | Directly assigned learners (plus legacy assessment group members) |

Scopes are exactly `ALL` and `SELECTED`.

Existing assessments migrate to `SELECTED` and their direct and group
assignments remain untouched. Previously public problems, learning paths,
contests and published Data Lab datasets migrate to `ALL`. Existing PRIVATE
datasets remain PRIVATE regardless of their scope column. Existing submissions,
attempts, results, ratings, and learner progress are not removed or rewritten.

## Which features are included?

- **Problems**: Foundation, DSA, Python, SQL, Pandas/NumPy, PySpark, AI/ML,
  deep learning, Linux, Excel and Tableau practice all use the same underlying
  `Problem` entity. Multiple-choice quizzes and numerical questions also
  use this common model.
- **Timed and mixed assessments**: `Assessment` supports both scopes and
  retains existing per-student and per-group assignment tables.
- **Contests** and **learning paths**: audience checks are applied to listing,
  detail, participation and enrollment as relevant.
- **Published Data Lab datasets**: audience applies to library visibility,
  downloads and new practice executions. Personal datasets remain private.
- Administrator-managed evaluator/test datasets, individual results, account
  profiles and audit logs are inherently private; these do **not** support ALL.
- Built-in stateless Excel/Tableau graders and static multi-tool examples are
  not student-assigned, publishable entities. They are intentionally not
  given artificial assignment tables.
- The current account system has `learner` and `admin` roles. There is no
  instructor/teacher authoring role to grant permissions to yet.

## Admin workflow

Use **Administration → Assessment Management, Problems, Contests, Paths or
Dataset Library**. Choose **All Students** for general training content or
**Selected Students Only** to search and select registered active learners.

You can publish an ALL item with no assigned students. SELECTED requires at
least one direct student, or for timed assessments an existing group assignment.
Selected students may be changed after publication through **Manage access**
on the existing record. Published audience changes require an impact preview
and explicit confirmation. Prior submissions, attempts, progress and ratings
are retained, although a removed student cannot start new restricted work.

The separate admin-managed evaluator dataset store is not a student library;
its access must remain administrator-only.

## HTTP API

These operations require an administrator session:

- `GET /api/v1/admin/students?q=<search>&limit=50`
  returns active learner IDs, usernames and display names only.
- `GET /api/v1/admin/access/{kind}/{identifier}` returns the current scope and
  direct assignment IDs.
- `POST /api/v1/admin/access/{kind}/{identifier}/preview` previews the
  proposed scope and assignment change.
- `PATCH /api/v1/admin/access/{kind}/{identifier}` applies the change with
  `confirm_impact: true` when it affects published content.

Kinds are `problem`, `contest`, `path`, `assessment`, and `dataset`.
The `identifier` is a slug except for assessments and datasets (UUID IDs).

Example for a **draft** assessment with no selected learners:

```json
{
  "access_scope": "ALL",
  "assigned_user_ids": []
}
```

Example for changing an existing published assessment to selected learners
after reviewing the impact:

```json
{
  "access_scope": "SELECTED",
  "assigned_user_ids": [17, 42],
  "confirm_impact": true,
  "reason": "Allocate this exercise to the November cohort"
}
```

The access manager validates IDs against **active registered learner accounts**.
For assessments, existing group assignments still grant access when the scope
is SELECTED. Account suspension continues to block sign-in regardless of
scope. Invalid/expired authentication cannot reveal targeted content.

The frontend BFF at `/api/admin/*` forwards these admin calls. Student
catalogs, details, direct judge submissions, timed attempts, contest
registration/submissions and Data Lab downloads/practice are secured by
backend audience checks, not UI visibility alone. For timed assessments,
existing open/close windows, max attempts and server timer still apply.

## Deployment and verification

Run migrations before enabling the updated API:

```sh
cd backend
alembic upgrade head
```

For Docker Compose, the one-shot `migrate` service runs Alembic on startup.
Do not downgrade against live data without a tested backup.

Suggested verification:

```sh
PYTHONPATH=backend pytest -q backend/tests/test_student_access.py backend/tests/test_advanced.py backend/tests/test_admin.py backend/tests/test_catalog.py backend/tests/test_contests.py backend/tests/test_learning.py backend/tests/test_submissions.py
cd frontend && npm ci && npm run typecheck && npm run build && npm test
```

The existing frontend package currently does not have an ESLint script; add an
ESLint configuration and run it separately if linting is a release requirement.

Security note: a finalized/archived attempt or submission remains viewable to
its rightful owner even if future access is revoked. Audience changes are not
retroactive deletion of personal work or results.
