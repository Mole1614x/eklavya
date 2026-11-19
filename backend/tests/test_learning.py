from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.learning import current_streak, record_daily_completion
from app.models import DailyChallenge, DailyChallengeCompletion, Profile, Submission, User, UserProgress, XPTransaction
from app.seed import seed


def test_daily_completion_reward_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'daily.db'}")
    Base.metadata.create_all(engine)
    day = datetime.now(timezone.utc).date() - timedelta(days=2)
    with Session(engine) as db:
        seed(db)
        user = User(email="daily@example.com", username="daily", password_hash="unused", profile=Profile(display_name="Daily"))
        db.add(user); db.flush()
        challenge = DailyChallenge(challenge_date=day, problem_slug="parity-check", xp_reward=20)
        db.add(challenge); db.flush()
        submission = Submission(
            id="daily-submit", user_id=user.id, problem_slug="parity-check", language="python", source_code="pass",
            mode="SUBMIT", status="FINISHED", verdict="ACCEPTED", created_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
        )
        db.add(submission); db.flush()
        assert record_daily_completion(db, submission) is True
        assert record_daily_completion(db, submission) is False
        db.commit()
        assert db.get(UserProgress, user.id).xp == 20
        assert len(db.scalars(select(DailyChallengeCompletion)).all()) == 1
        assert len(db.scalars(select(XPTransaction).where(XPTransaction.source_type == "daily_challenge")).all()) == 1
    engine.dispose()


def test_streak_counts_consecutive_days(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'streak.db'}")
    Base.metadata.create_all(engine)
    today = datetime.now(timezone.utc).date()
    with Session(engine) as db:
        seed(db)
        user = User(email="streak@example.com", username="streak", password_hash="unused", profile=Profile(display_name="Streak"))
        db.add(user); db.flush()
        for offset in range(3):
            day = today - timedelta(days=offset)
            challenge = db.scalar(select(DailyChallenge).where(DailyChallenge.challenge_date == day))
            if challenge is None:
                challenge = DailyChallenge(challenge_date=day, problem_slug="parity-check")
                db.add(challenge); db.flush()
            submission = Submission(id=f"s-{offset}", user_id=user.id, problem_slug=challenge.problem_slug, language="python", source_code="pass", mode="SUBMIT", status="FINISHED", verdict="ACCEPTED", created_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc))
            db.add(submission); db.flush()
            assert record_daily_completion(db, submission)
        db.commit()
        assert current_streak(db, user.id) == 3
    engine.dispose()
