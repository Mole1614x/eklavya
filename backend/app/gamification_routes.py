from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import CurrentUser
from .cache import cache_key, get_public, set_public
from .main_dependencies import get_db
from .models import (
    Achievement, Profile, RankLevel, Submission, User, UserAchievement, UserProgress, XPTransaction,
)

router = APIRouter(prefix="/gamification", tags=["gamification"])
DB = Annotated[Session, Depends(get_db)]


@router.get("/ranks")
def ranks(db: DB) -> list[dict]:
    return [{"slug": rank.slug, "name": rank.name, "min_xp": rank.min_xp, "stars": rank.stars} for rank in db.scalars(select(RankLevel).order_by(RankLevel.position))]


@router.get("/leaderboard")
def leaderboard(
    db: DB, limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> list[dict]:
    key = cache_key("leaderboard", limit, offset)
    cached = get_public(key)
    if cached is not None:
        return cached
    rows = db.execute(select(User.username, Profile.display_name, UserProgress.xp, UserProgress.solved_count, RankLevel.name, RankLevel.stars).join(
        Profile, Profile.user_id == User.id,
    ).join(UserProgress, UserProgress.user_id == User.id).join(
        RankLevel, RankLevel.slug == UserProgress.current_rank_slug,
    ).where(User.is_active.is_(True)).order_by(UserProgress.xp.desc(), UserProgress.updated_at, User.id).limit(limit).offset(offset))
    result = [{"position": index, "username": row.username, "display_name": row.display_name, "xp": row.xp, "solved_count": row.solved_count, "rank": row.name, "stars": row.stars} for index, row in enumerate(rows, offset + 1)]
    set_public(key, result)
    return result


@router.get("/dashboard")
def dashboard(user: CurrentUser, db: DB) -> dict:
    progress = db.get(UserProgress, user.id)
    xp = progress.xp if progress else 0
    current = db.scalar(select(RankLevel).where(RankLevel.min_xp <= xp).order_by(RankLevel.min_xp.desc()).limit(1))
    following = db.scalar(select(RankLevel).where(RankLevel.min_xp > xp).order_by(RankLevel.min_xp).limit(1))
    accepted = db.scalar(select(func.count()).select_from(Submission).where(Submission.user_id == user.id, Submission.verdict == "ACCEPTED")) or 0
    total = db.scalar(select(func.count()).select_from(Submission).where(Submission.user_id == user.id, Submission.status == "FINISHED")) or 0
    return {
        "xp": xp, "solved_count": progress.solved_count if progress else 0,
        "rank": current.name if current else "Shishya", "stars": current.stars if current else 1,
        "next_rank": following.name if following else None, "next_rank_xp": following.min_xp if following else None,
        "accepted_submissions": accepted, "submission_accuracy": round(accepted / total * 100, 1) if total else 0,
    }


@router.get("/achievements")
def achievements(user: CurrentUser, db: DB) -> list[dict]:
    earned = {row.achievement_slug: row.awarded_at for row in db.scalars(select(UserAchievement).where(UserAchievement.user_id == user.id))}
    return [{"slug": item.slug, "name": item.name, "description": item.description, "xp_reward": item.xp_reward, "earned_at": earned.get(item.slug)} for item in db.scalars(select(Achievement).order_by(Achievement.name))]


@router.get("/insights")
def insights(user: CurrentUser, db: DB) -> dict:
    daily = db.execute(select(func.date(Submission.created_at).label("day"), func.count().label("count")).where(
        Submission.user_id == user.id,
    ).group_by(func.date(Submission.created_at)).order_by(func.date(Submission.created_at).desc()).limit(30)).all()
    xp = db.execute(select(func.date(XPTransaction.created_at).label("day"), func.sum(XPTransaction.amount).label("amount")).where(
        XPTransaction.user_id == user.id,
    ).group_by(func.date(XPTransaction.created_at)).order_by(func.date(XPTransaction.created_at))).all()
    topics = db.execute(select(Submission.problem_slug, func.count()).where(
        Submission.user_id == user.id, Submission.verdict == "ACCEPTED",
    ).group_by(Submission.problem_slug).order_by(func.count().desc()).limit(10)).all()
    return {
        "daily_activity": [{"day": str(row.day), "count": row.count} for row in reversed(daily)],
        "xp_growth": [{"day": str(row.day), "amount": row.amount} for row in xp],
        "solved_problems": [{"problem_slug": row[0], "accepted_submissions": row[1]} for row in topics],
    }
