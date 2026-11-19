from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .gamification import _update_rank
from .models import (
    Achievement, DailyChallenge, DailyChallengeCompletion, Submission, User, UserAchievement,
    UserProgress, XPTransaction,
)


def record_daily_completion(db: Session, submission: Submission) -> bool:
    submitted_day = submission.created_at.date()
    challenge = db.scalar(select(DailyChallenge).where(
        DailyChallenge.challenge_date == submitted_day,
        DailyChallenge.problem_slug == submission.problem_slug,
    ))
    if challenge is None:
        return False
    existing = db.scalar(select(DailyChallengeCompletion.id).where(
        DailyChallengeCompletion.user_id == submission.user_id,
        DailyChallengeCompletion.daily_challenge_id == challenge.id,
    ))
    if existing is not None:
        return False
    db.scalar(select(User.id).where(User.id == submission.user_id).with_for_update())
    completion = DailyChallengeCompletion(
        user_id=submission.user_id, daily_challenge_id=challenge.id, submission_id=submission.id,
    )
    db.add(completion)
    db.add(XPTransaction(
        user_id=submission.user_id, amount=challenge.xp_reward, reason="Daily Sadhana completion",
        source_type="daily_challenge", source_id=str(challenge.challenge_date),
    ))
    progress = db.get(UserProgress, submission.user_id)
    if progress is None:
        progress = UserProgress(user_id=submission.user_id, xp=0, solved_count=0, current_rank_slug="shishya")
        db.add(progress)
    progress.xp += challenge.xp_reward
    db.flush()
    streak = current_streak(db, submission.user_id, submitted_day)
    for length, slug in ((7, "seven-day-streak"), (30, "thirty-day-streak")):
        if streak >= length:
            _award_streak(db, progress, slug)
    _update_rank(db, progress)
    return True


def current_streak(db: Session, user_id: int, as_of: date | None = None) -> int:
    days = list(db.scalars(select(DailyChallenge.challenge_date).join(
        DailyChallengeCompletion, DailyChallengeCompletion.daily_challenge_id == DailyChallenge.id,
    ).where(DailyChallengeCompletion.user_id == user_id).order_by(DailyChallenge.challenge_date.desc())))
    if not days:
        return 0
    anchor = as_of or datetime.now(timezone.utc).date()
    if days[0] not in {anchor, anchor - timedelta(days=1)}:
        return 0
    streak = 1
    for previous, current in zip(days, days[1:]):
        if previous - current != timedelta(days=1):
            break
        streak += 1
    return streak


def _award_streak(db: Session, progress: UserProgress, slug: str) -> None:
    if db.scalar(select(UserAchievement.id).where(UserAchievement.user_id == progress.user_id, UserAchievement.achievement_slug == slug)) is not None:
        return
    achievement = db.get(Achievement, slug)
    if achievement is None:
        return
    db.add(UserAchievement(user_id=progress.user_id, achievement_slug=slug))
    db.add(XPTransaction(user_id=progress.user_id, amount=achievement.xp_reward, reason=achievement.name, source_type="achievement", source_id=slug))
    progress.xp += achievement.xp_reward
