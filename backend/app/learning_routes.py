from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import CurrentUser
from .learning import current_streak
from .main_dependencies import get_db
from .models import (
    DailyChallenge, DailyChallengeCompletion, LearningPath, LearningPathProblem, LearningPathProgress,
    Problem, Submission,
)

router = APIRouter(prefix="/learning", tags=["learning"])
DB = Annotated[Session, Depends(get_db)]


@router.get("/daily")
def daily(db: DB) -> dict:
    today = datetime.now(timezone.utc).date()
    row = db.execute(select(DailyChallenge, Problem).join(Problem, Problem.slug == DailyChallenge.problem_slug).where(DailyChallenge.challenge_date == today)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Daily challenge is not scheduled")
    challenge, problem = row
    return {"date": str(today), "timezone": "UTC", "problem_slug": problem.slug, "title": problem.title, "difficulty": problem.difficulty, "xp_reward": challenge.xp_reward}


@router.get("/daily/history")
def daily_history(user: CurrentUser, db: DB) -> dict:
    rows = db.execute(select(DailyChallenge.challenge_date, Problem.title, DailyChallengeCompletion.completed_at).join(
        DailyChallengeCompletion, DailyChallengeCompletion.daily_challenge_id == DailyChallenge.id,
    ).join(Problem, Problem.slug == DailyChallenge.problem_slug).where(
        DailyChallengeCompletion.user_id == user.id,
    ).order_by(DailyChallenge.challenge_date.desc()).limit(90)).all()
    return {"streak": current_streak(db, user.id), "timezone": "UTC", "completions": [{"date": str(row.challenge_date), "title": row.title, "completed_at": row.completed_at} for row in rows]}


@router.get("/paths")
def paths(db: DB) -> list[dict]:
    counts = dict(db.execute(select(LearningPathProblem.path_slug, func.count()).group_by(LearningPathProblem.path_slug)).all())
    return [{"slug": item.slug, "title": item.title, "description": item.description, "prerequisites": item.prerequisites, "problem_count": counts.get(item.slug, 0)} for item in db.scalars(select(LearningPath).order_by(LearningPath.title))]


@router.get("/paths/{slug}")
def path_detail(slug: str, user: CurrentUser, db: DB) -> dict:
    path = db.get(LearningPath, slug)
    if path is None:
        raise HTTPException(status_code=404, detail="Learning path not found")
    assignments = db.execute(select(LearningPathProblem, Problem).join(Problem, Problem.slug == LearningPathProblem.problem_slug).where(
        LearningPathProblem.path_slug == slug,
    ).order_by(LearningPathProblem.position)).all()
    solved = set(db.scalars(select(Submission.problem_slug).where(Submission.user_id == user.id, Submission.mode == "SUBMIT", Submission.verdict == "ACCEPTED")).all())
    progress = db.scalar(select(LearningPathProgress).where(LearningPathProgress.user_id == user.id, LearningPathProgress.path_slug == slug))
    completed = sum(row.Problem.slug in solved for row in assignments)
    if progress and assignments and completed == len(assignments) and progress.completed_at is None:
        progress.completed_at = datetime.now(timezone.utc); db.commit()
    return {"slug": slug, "title": path.title, "description": path.description, "prerequisites": path.prerequisites, "enrolled": progress is not None, "completion_percentage": round(completed / len(assignments) * 100) if assignments else 0, "problems": [{"slug": row.Problem.slug, "title": row.Problem.title, "position": row.LearningPathProblem.position, "milestone": row.LearningPathProblem.milestone, "completed": row.Problem.slug in solved} for row in assignments]}


@router.post("/paths/{slug}/enroll", status_code=status.HTTP_204_NO_CONTENT)
def enroll(slug: str, user: CurrentUser, db: DB) -> None:
    if db.get(LearningPath, slug) is None:
        raise HTTPException(status_code=404, detail="Learning path not found")
    exists = db.scalar(select(LearningPathProgress.id).where(LearningPathProgress.user_id == user.id, LearningPathProgress.path_slug == slug))
    if exists is None:
        db.add(LearningPathProgress(user_id=user.id, path_slug=slug)); db.commit()
