from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.app.database import Session
from backend.app.models import Submission, TestCase
from judge.celery_app import app
from judge.executor import execute, outputs_match


@app.task(name="judge.evaluate")
def evaluate(submission_id: str) -> None:
    with Session() as db:
        submission = db.scalar(select(Submission).where(Submission.id == submission_id).with_for_update())
        now = datetime.now(timezone.utc)
        if submission is None or submission.status in {"FINISHED", "SYSTEM_ERROR"}:
            return
        if submission.status == "RUNNING" and submission.started_at is not None:
            started_at = submission.started_at if submission.started_at.tzinfo else submission.started_at.replace(tzinfo=timezone.utc)
            if started_at > now - timedelta(seconds=45):
                return
        submission.status = "RUNNING"
        submission.started_at = now
        submission.passed_tests = 0
        db.commit()
        try:
            cases = list(db.scalars(select(TestCase).where(
                TestCase.problem_slug == submission.problem_slug,
                *([] if submission.mode == "SUBMIT" else [TestCase.is_hidden.is_(False)]),
            ).order_by(TestCase.position, TestCase.id)))
            submission.total_tests = len(cases)
            if not cases:
                _finish(submission, "UNSUPPORTED_EVALUATOR", "No evaluator is configured for this problem.")
                db.commit()
                return
            total_ms = 0
            for case in cases:
                result = execute(submission.language, submission.source_code, case.input_data)
                total_ms += result.execution_ms
                if result.verdict != "COMPLETED":
                    _finish(submission, result.verdict, result.output, total_ms)
                    db.commit()
                    return
                if not outputs_match(result.output, case.expected_output, case.tolerance):
                    output = result.output if not case.is_hidden else "A hidden test case did not match the expected output."
                    _finish(submission, "WRONG_ANSWER", output, total_ms)
                    db.commit()
                    return
                submission.passed_tests += 1
            _finish(submission, "ACCEPTED", "All selected test cases passed.", total_ms)
            db.commit()
        except Exception:
            submission.status = "SYSTEM_ERROR"
            submission.verdict = "SYSTEM_ERROR"
            submission.output = "The judge could not evaluate this submission."
            submission.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise


def _finish(submission: Submission, verdict: str, output: str, execution_ms: int | None = None) -> None:
    submission.status = "FINISHED"
    submission.verdict = verdict
    submission.output = output[:64_000]
    submission.execution_ms = execution_ms
    submission.finished_at = datetime.now(timezone.utc)
