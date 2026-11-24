import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from backend.app.database import Session
from backend.app.cache import invalidate_public
from backend.app.models import DatasetPracticeRun, PracticeDataset, ProblemEvaluator, Submission, TestCase
from backend.app.gamification import award_submission
from backend.app.learning import record_daily_completion
from judge.celery_app import app
from judge.executor import execute, outputs_match
from judge.specialized import evaluate_answer, execute_ai, execute_bigdata, execute_data, execute_sql, extract_result, structured_match
from judge.advanced import evaluate_expression, execute_bash, execute_dataset_practice


@app.task(name="judge.evaluate", bind=True, max_retries=2)
def evaluate(self, submission_id: str) -> None:
    with Session() as db:
        submission = db.scalar(select(Submission).where(Submission.id == submission_id).with_for_update())
        now = datetime.now(timezone.utc)
        if submission is None or submission.status in {"FINISHED", "SYSTEM_ERROR", "CANCELLED"}:
            return
        if submission.cancel_requested_at is not None:
            _cancel(submission, now)
            db.commit()
            return
        if submission.status == "RUNNING" and submission.started_at is not None:
            started_at = submission.started_at if submission.started_at.tzinfo else submission.started_at.replace(tzinfo=timezone.utc)
            if started_at > now - timedelta(seconds=45):
                delay = max(1, 46 - int((now - started_at).total_seconds()))
                raise self.retry(countdown=delay)
        submission.status = "RUNNING"
        submission.started_at = now
        submission.attempt_count += 1
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
            evaluator = db.get(ProblemEvaluator, submission.problem_slug)
            for case in cases:
                if evaluator is None:
                    result = execute(submission.language, submission.source_code, case.input_data)
                elif evaluator.kind == "sql":
                    result = execute_sql(submission.source_code, case.input_data)
                elif evaluator.kind in {"numerical", "multiple_choice"}:
                    result = evaluate_answer(evaluator.kind, submission.source_code)
                elif evaluator.kind in {"excel_formula", "tableau_expression"}:
                    result = evaluate_expression(evaluator.kind, submission.source_code, case.input_data)
                elif evaluator.kind == "bash_sandbox":
                    result = execute_bash(submission.source_code, case.input_data)
                elif evaluator.kind in {"pyspark_function", "mapreduce_function"}:
                    result = execute_bigdata(evaluator.kind, submission.source_code, case.input_data, evaluator.config)
                elif evaluator.kind in {"numpy_ai_function", "python_ai_function", "torch_function"}:
                    result = execute_ai(evaluator.kind, submission.source_code, case.input_data, evaluator.config)
                else:
                    result = execute_data(evaluator.kind, submission.source_code, case.input_data, evaluator.config)
                total_ms += result.execution_ms
                db.refresh(submission, attribute_names=["status", "cancel_requested_at"])
                if submission.cancel_requested_at is not None or submission.status == "CANCELLED":
                    _cancel(submission)
                    db.commit()
                    return
                if result.verdict != "COMPLETED":
                    _finish(submission, result.verdict, result.output, total_ms)
                    db.commit()
                    return
                if evaluator is not None and evaluator.kind == "data_practice_function":
                    # The reference runs in a separate sandbox, never alongside learner code.
                    reference_source = (evaluator.config or {}).get("reference_source")
                    if not reference_source:
                        _finish(submission, "SYSTEM_ERROR", "This practice challenge is missing its reference solution.", total_ms)
                        db.commit()
                        return
                    reference_result = execute_data(
                        "data_practice_function", reference_source, case.input_data,
                        {"function": "solve", "output": "json"},
                    )
                    if reference_result.verdict != "COMPLETED":
                        _finish(submission, "SYSTEM_ERROR", "This practice challenge could not be graded.", total_ms)
                        db.commit()
                        return
                    try:
                        matched = structured_match(
                            extract_result(result.output), extract_result(reference_result.output),
                            case.tolerance if case.tolerance is not None else (evaluator.config or {}).get("tolerance", 1e-6),
                        )
                    except (ValueError, TypeError):
                        matched = False
                elif evaluator is None or evaluator.kind == "bash_sandbox":
                    matched = outputs_match(result.output, case.expected_output, case.tolerance)
                else:
                    try:
                        matched = structured_match(
                            extract_result(result.output), json.loads(case.expected_output),
                            case.tolerance if case.tolerance is not None else (evaluator.config or {}).get("tolerance"),
                        )
                    except (ValueError, json.JSONDecodeError):
                        matched = False
                if not matched:
                    output = result.output if not case.is_hidden else "A hidden test case did not match the expected output."
                    _finish(submission, "WRONG_ANSWER", output, total_ms)
                    db.commit()
                    return
                submission.passed_tests += 1
            _finish(submission, "ACCEPTED", "All selected test cases passed.", total_ms)
            award_submission(db, submission)
            record_daily_completion(db, submission)
            db.commit()
            invalidate_public("leaderboard", "contest")
        except OperationalError as error:
            db.rollback()
            retry_submission = db.scalar(
                select(Submission).where(Submission.id == submission_id).with_for_update()
            )
            if retry_submission is not None and retry_submission.status == "RUNNING":
                retry_submission.status = "QUEUED"
                retry_submission.started_at = None
                db.commit()
            raise self.retry(exc=error, countdown=1)
        except Exception:
            db.rollback()
            failed = db.scalar(select(Submission).where(Submission.id == submission_id).with_for_update())
            if failed is not None and failed.status not in {"FINISHED", "SYSTEM_ERROR", "CANCELLED"}:
                failed.status = "SYSTEM_ERROR"
                failed.verdict = "SYSTEM_ERROR"
                failed.output = "The judge could not evaluate this submission."
                failed.finished_at = datetime.now(timezone.utc)
                db.commit()
            raise


@app.task(name="judge.dataset_practice")
def evaluate_dataset_practice_run(run_id: str) -> None:
    with Session() as db:
        run = db.scalar(select(DatasetPracticeRun).where(DatasetPracticeRun.id == run_id).with_for_update())
        if run is None or run.status in {"FINISHED", "SYSTEM_ERROR"}:
            return
        dataset = db.get(PracticeDataset, run.dataset_id)
        if dataset is None or dataset.status == "ARCHIVED":
            run.status, run.output, run.finished_at = "SYSTEM_ERROR", "The dataset is no longer available.", datetime.now(timezone.utc)
            db.commit(); return
        run.status, run.started_at = "RUNNING", datetime.now(timezone.utc)
        db.commit()
        try:
            result = execute_dataset_practice(run.technology, run.source_code, Path(dataset.storage_path), dataset.format)
            db.refresh(run)
            run.execution_ms = result.execution_ms
            run.finished_at = datetime.now(timezone.utc)
            if result.verdict == "COMPLETED":
                run.status = "FINISHED"
                try: run.output = json.dumps(extract_result(result.output), ensure_ascii=False)[:64_000]
                except ValueError: run.status, run.output = "SYSTEM_ERROR", "The isolated Data Lab runner returned an invalid result."
            else:
                run.status = "SYSTEM_ERROR" if result.verdict == "SYSTEM_ERROR" else "FINISHED"
                run.output = result.output[:64_000]
            db.commit()
        except Exception:
            db.rollback()
            failed = db.get(DatasetPracticeRun, run_id)
            if failed is not None:
                failed.status, failed.output, failed.finished_at = "SYSTEM_ERROR", "The isolated Data Lab run could not be completed.", datetime.now(timezone.utc)
                db.commit()
            raise


def _finish(submission: Submission, verdict: str, output: str, execution_ms: int | None = None) -> None:
    submission.status = "FINISHED"
    submission.verdict = verdict
    submission.output = output[:64_000]
    submission.execution_ms = execution_ms
    submission.finished_at = datetime.now(timezone.utc)


def _cancel(submission: Submission, now: datetime | None = None) -> None:
    submission.status = "CANCELLED"
    submission.verdict = "CANCELLED"
    submission.output = "Submission cancelled by the user."
    submission.finished_at = now or datetime.now(timezone.utc)
