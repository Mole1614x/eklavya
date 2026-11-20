from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import Base
from backend.app.models import Submission, User, UserProgress, XPTransaction
from backend.app.seed import seed
from judge import tasks
from judge.executor import Execution


def lifecycle_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'lifecycle.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        user = User(
            email="judge@example.com", username="judge-user", password_hash="not-used",
            profile=None,
        )
        db.add(user)
        db.flush()
        user_id = user.id
        db.commit()
    return engine, user_id


def test_verified_submission_lifecycle_awards_once(tmp_path, monkeypatch):
    engine, user_id = lifecycle_database(tmp_path)
    factory = sessionmaker(engine)
    monkeypatch.setattr(tasks, "Session", factory)

    def execute_case(language, source, input_data):
        value = int(input_data)
        return Execution("COMPLETED", "Even\n" if value % 2 == 0 else "Odd\n", 4, 1024)

    monkeypatch.setattr(tasks, "execute", execute_case)
    with Session(engine) as db:
        db.add(Submission(
            id="accepted", user_id=user_id, problem_slug="parity-check", language="python",
            source_code="verified by isolated executor", mode="SUBMIT",
        ))
        db.commit()

    tasks.evaluate.run("accepted")
    tasks.evaluate.run("accepted")
    with Session(engine) as db:
        submission = db.get(Submission, "accepted")
        assert (submission.status, submission.verdict) == ("FINISHED", "ACCEPTED")
        assert (submission.passed_tests, submission.total_tests) == (2, 2)
        assert submission.execution_ms == 8
        progress = db.get(UserProgress, user_id)
        assert progress.solved_count == 1
        assert len(db.scalars(select(XPTransaction).where(
            XPTransaction.user_id == user_id,
            XPTransaction.source_type == "first_solve",
        )).all()) == 1
    engine.dispose()


def test_hidden_failure_is_masked_and_never_awards_xp(tmp_path, monkeypatch):
    engine, user_id = lifecycle_database(tmp_path)
    monkeypatch.setattr(tasks, "Session", sessionmaker(engine))

    def wrong_hidden_case(language, source, input_data):
        return Execution("COMPLETED", "Even\n", 2)

    monkeypatch.setattr(tasks, "execute", wrong_hidden_case)
    with Session(engine) as db:
        db.add(Submission(
            id="wrong", user_id=user_id, problem_slug="parity-check", language="python",
            source_code="incorrect", mode="SUBMIT",
        ))
        db.commit()

    tasks.evaluate.run("wrong")
    with Session(engine) as db:
        submission = db.get(Submission, "wrong")
        assert submission.verdict == "WRONG_ANSWER"
        assert submission.passed_tests == 1
        assert submission.output == "A hidden test case did not match the expected output."
        assert db.get(UserProgress, user_id) is None
        assert db.scalar(select(XPTransaction.id).where(XPTransaction.user_id == user_id)) is None
    engine.dispose()


def test_cancelled_delivery_never_executes_or_awards(tmp_path, monkeypatch):
    engine, user_id = lifecycle_database(tmp_path)
    monkeypatch.setattr(tasks, "Session", sessionmaker(engine))
    monkeypatch.setattr(tasks, "execute", lambda *args: (_ for _ in ()).throw(AssertionError("must not execute")))
    with Session(engine) as db:
        db.add(Submission(
            id="cancelled-before-start", user_id=user_id, problem_slug="parity-check",
            language="python", source_code="print('Even')", mode="SUBMIT",
            cancel_requested_at=datetime.now(timezone.utc),
        ))
        db.commit()
    tasks.evaluate.run("cancelled-before-start")
    with Session(engine) as db:
        item = db.get(Submission, "cancelled-before-start")
        assert (item.status, item.verdict, item.attempt_count) == ("CANCELLED", "CANCELLED", 0)
        assert db.get(UserProgress, user_id) is None
    engine.dispose()


def test_stale_worker_lease_is_reclaimed_safely(tmp_path, monkeypatch):
    engine, user_id = lifecycle_database(tmp_path)
    monkeypatch.setattr(tasks, "Session", sessionmaker(engine))
    monkeypatch.setattr(tasks, "execute", lambda language, source, value: Execution(
        "COMPLETED", "Even\n" if int(value) % 2 == 0 else "Odd\n", 3,
    ))
    with Session(engine) as db:
        db.add(Submission(
            id="stale", user_id=user_id, problem_slug="parity-check", language="python",
            source_code="verified", mode="SUBMIT", status="RUNNING", attempt_count=1,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        ))
        db.commit()
    tasks.evaluate.run("stale")
    with Session(engine) as db:
        item = db.get(Submission, "stale")
        assert (item.status, item.verdict, item.attempt_count) == ("FINISHED", "ACCEPTED", 2)
    engine.dispose()
