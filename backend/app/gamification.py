from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    Achievement, Problem, RankHistory, RankLevel, Submission, User, UserAchievement, UserProgress, XPTransaction,
)

XP_BY_DIFFICULTY = {"Beginner": 20, "Easy": 30, "Medium": 50, "Hard": 80}


def award_submission(db: Session, submission: Submission) -> bool:
    if submission.mode != "SUBMIT" or submission.verdict != "ACCEPTED":
        return False
    db.scalar(select(User.id).where(User.id == submission.user_id).with_for_update())
    exists = db.scalar(select(XPTransaction.id).where(
        XPTransaction.user_id == submission.user_id,
        XPTransaction.source_type == "first_solve",
        XPTransaction.source_id == submission.problem_slug,
    ))
    if exists is not None:
        return False
    problem = db.get(Problem, submission.problem_slug)
    if problem is None:
        return False
    progress = db.get(UserProgress, submission.user_id)
    if progress is None:
        progress = UserProgress(user_id=submission.user_id)
        db.add(progress)
        db.flush()
    amount = XP_BY_DIFFICULTY[problem.difficulty]
    db.add(XPTransaction(
        user_id=submission.user_id, amount=amount, reason=f"Solved {problem.title}",
        source_type="first_solve", source_id=problem.slug,
    ))
    progress.xp += amount
    progress.solved_count += 1
    _award_achievements(db, progress, problem)
    _update_rank(db, progress)
    return True


def _award_achievements(db: Session, progress: UserProgress, problem: Problem) -> None:
    achievements = list(db.scalars(select(Achievement)))
    for achievement in achievements:
        criteria = achievement.criteria
        qualifies = criteria.get("solved") == progress.solved_count
        qualifies |= criteria.get("difficulty") == problem.difficulty
        if "category" in criteria:
            count = _solved_matching(db, progress.user_id, Problem.category == criteria["category"])
            qualifies |= count >= criteria["count"]
        if "topic" in criteria:
            count = _solved_matching(db, progress.user_id, Problem.topic == criteria["topic"])
            qualifies |= count >= criteria["count"]
        if not qualifies:
            continue
        exists = db.scalar(select(UserAchievement.id).where(
            UserAchievement.user_id == progress.user_id,
            UserAchievement.achievement_slug == achievement.slug,
        ))
        if exists is not None:
            continue
        db.add(UserAchievement(user_id=progress.user_id, achievement_slug=achievement.slug))
        if achievement.xp_reward:
            db.add(XPTransaction(
                user_id=progress.user_id, amount=achievement.xp_reward, reason=achievement.name,
                source_type="achievement", source_id=achievement.slug,
            ))
            progress.xp += achievement.xp_reward


def _solved_matching(db: Session, user_id: int, predicate) -> int:
    return db.scalar(select(func.count(func.distinct(Submission.problem_slug))).join(
        Problem, Problem.slug == Submission.problem_slug,
    ).where(Submission.user_id == user_id, Submission.verdict == "ACCEPTED", Submission.mode == "SUBMIT", predicate)) or 0


def _update_rank(db: Session, progress: UserProgress) -> None:
    rank = db.scalar(select(RankLevel).where(RankLevel.min_xp <= progress.xp).order_by(RankLevel.min_xp.desc()).limit(1))
    if rank is not None and progress.current_rank_slug != rank.slug:
        progress.current_rank_slug = rank.slug
        db.add(RankHistory(user_id=progress.user_id, rank_slug=rank.slug))
