from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.gamification import award_submission
from app.models import Profile, RankLevel, Submission, User, UserProgress, XPTransaction
from app.seed import seed


def test_verified_first_solve_awards_once_and_updates_rank(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'gamification.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        user = User(email="ranked@example.com", username="ranked", password_hash="unused", profile=Profile(display_name="Ranked"))
        db.add(user)
        db.flush()
        submission = Submission(
            id="accepted-1", user_id=user.id, problem_slug="parity-check", language="python",
            source_code="pass", mode="SUBMIT", status="FINISHED", verdict="ACCEPTED",
        )
        db.add(submission)
        db.flush()
        assert award_submission(db, submission) is True
        assert award_submission(db, submission) is False
        db.commit()
        progress = db.get(UserProgress, user.id)
        assert progress.solved_count == 1
        assert progress.xp == 45  # 20 beginner XP + 25 first-solve badge XP
        assert len(db.scalars(select(XPTransaction)).all()) == 2
        assert db.get(RankLevel, progress.current_rank_slug).name == "Shishya"
    engine.dispose()


def test_run_and_failed_submissions_never_award(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'no-award.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        user = User(email="test@example.com", username="test", password_hash="unused", profile=Profile(display_name="Test"))
        db.add(user); db.flush()
        run = Submission(id="run", user_id=user.id, problem_slug="parity-check", language="python", source_code="", mode="RUN", status="FINISHED", verdict="ACCEPTED")
        failed = Submission(id="failed", user_id=user.id, problem_slug="parity-check", language="python", source_code="", mode="SUBMIT", status="FINISHED", verdict="WRONG_ANSWER")
        db.add_all([run, failed]); db.flush()
        assert award_submission(db, run) is False
        assert award_submission(db, failed) is False
        assert db.get(UserProgress, user.id) is None
    engine.dispose()
