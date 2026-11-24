# Assessment scheduling and administration

## Why "Assessment is outside its permitted window" appears

Learners can start an assessment only when all of these hold:

1. Publication status is `PUBLISHED`.
2. Learner has access under the existing `ALL` / `SELECTED` rules.
3. Current server UTC time is at or after `opens_at` and strictly before `closes_at`.
4. Their attempt limit has not been reached.

The learner's local timezone changes how dates are displayed, **not** backend authorization.
A published assessment can still be UPCOMING or CLOSED.

## Guided Admin Control Center workflow

On **Admin → Assessment Management → Create assessment**:

- Enter a title, description, type and duration.
- Add one or more problems from the question bank; a known problem slug can also be entered.
- Choose **Available immediately after publication** (default) or **Schedule for later**.
- Choose the closing date and time in the browser's local timezone.
- Set **All Students** (no individual assignments) or **Selected Students Only** (choose learners and/or existing learner groups).
- Leave **Publish immediately after creating** off to save a draft; enable it to make the assessment eligible for learners as soon as its opening time arrives.

Dates are transmitted as ISO 8601 UTC instants, so local timezone interpretation is unambiguous.

## Editing an existing scheduled assessment

Each assessment card shows DRAFT, UPCOMING, AVAILABLE or CLOSED and its exact
opening/closing times. Open **Manage schedule and student access → Edit schedule**.

An admin can change `opens_at`, `closes_at` and `duration_minutes` **only while
no attempt has started**. A failed change leaves the previous schedule untouched.
All changes are audited. Existing assessments with attempts cannot be rescheduled
because doing so would change a live or graded attempt's fairness; create a new
assessment instead.

Endpoint:

```http
PATCH /api/v1/advanced/admin/assessments/{assessment_id}/schedule
Content-Type: application/json

{
  "opens_at": "2026-11-24T05:00:00Z",
  "closes_at": "2026-11-25T05:00:00Z",
  "duration_minutes": 90,
  "reason": "Correct the initial opening time"
}
```

Requires the existing administrator authentication and only succeeds with
a valid window, duration 1–480 minutes, and zero previous attempts. Server
timers, attempt limits, student targeting, and results are unchanged.

## Local verification

```bash
PYTHONPATH=backend pytest -q backend/tests/test_advanced.py
cd frontend && npm run typecheck && npm run build && npm test
```

The user-facing assessment list continues to enforce schedules on the backend,
not just display a badge; the badge is descriptive.
