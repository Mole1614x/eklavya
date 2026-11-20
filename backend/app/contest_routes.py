from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import CurrentUser, require_admin
from .cache import cache_key, get_public, invalidate_public, set_public
from .gamification import award_achievement
from .judge_client import Enqueuer
from .main_dependencies import get_db
from .models import (
    Contest, ContestProblem, ContestRating, ContestRegistration, ContestSubmission, Problem,
    Profile, Submission, User,
)
from .schemas_contests import (
    ContestCreate, ContestCreated, ContestDetail, ContestHistoryItem, ContestParticipant,
    ContestStanding, ContestSummary,
)
from .schemas_submissions import SubmissionCreate, SubmissionRead

router = APIRouter(prefix="/contests", tags=["contests"])
DB = Annotated[Session, Depends(get_db)]


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("", response_model=list[ContestSummary])
def contests(db: DB) -> list[dict]:
    key = cache_key("contest", "list")
    cached = get_public(key)
    if cached is not None:
        return cached
    now = datetime.now(timezone.utc)
    result = [
        {
            "slug": item.slug, "title": item.title, "description": item.description,
            "starts_at": item.starts_at, "ends_at": item.ends_at,
            "status": contest_status(item, now), "is_rated": item.is_rated,
        }
        for item in db.scalars(select(Contest).where(Contest.publication_status != "DRAFT").order_by(Contest.starts_at.desc()).limit(50))
    ]
    set_public(key, result)
    return result


@router.get("/me/history", response_model=list[ContestHistoryItem])
def contest_history(user: CurrentUser, db: DB) -> list[dict]:
    rows = db.execute(
        select(ContestRating, Contest)
        .join(Contest, Contest.id == ContestRating.contest_id)
        .where(ContestRating.user_id == user.id)
        .order_by(Contest.ends_at.desc())
    ).all()
    return [
        {
            "slug": contest.slug, "title": contest.title, "position": rating.position,
            "rating_before": rating.rating_before, "rating_after": rating.rating_after,
            "delta": rating.rating_after - rating.rating_before, "ended_at": contest.ends_at,
        }
        for rating, contest in rows
    ]


@router.get("/{slug}", response_model=ContestDetail)
def contest_detail(slug: str, db: DB) -> dict:
    contest = find_contest(db, slug)
    now = datetime.now(timezone.utc)
    problems = []
    if aware(contest.starts_at) <= now:
        rows = db.execute(
            select(ContestProblem, Problem)
            .join(Problem, Problem.slug == ContestProblem.problem_slug)
            .where(ContestProblem.contest_id == contest.id)
            .order_by(ContestProblem.position)
        ).all()
        problems = [
            {
                "slug": problem.slug, "title": problem.title, "difficulty": problem.difficulty,
                "position": contest_problem.position, "points": contest_problem.points,
            }
            for contest_problem, problem in rows
        ]
    return {
        "slug": contest.slug, "title": contest.title, "description": contest.description,
        "starts_at": contest.starts_at, "ends_at": contest.ends_at,
        "status": contest_status(contest, now), "is_rated": contest.is_rated, "problems": problems,
    }


@router.get("/{slug}/me", response_model=ContestParticipant)
def participant_status(slug: str, user: CurrentUser, db: DB) -> dict:
    contest = find_contest(db, slug)
    registered = db.scalar(
        select(ContestRegistration.id).where(
            ContestRegistration.contest_id == contest.id, ContestRegistration.user_id == user.id,
        )
    ) is not None
    rating = db.scalar(
        select(ContestRating.rating_after)
        .where(ContestRating.user_id == user.id)
        .order_by(ContestRating.id.desc())
        .limit(1)
    ) or 1200
    submissions = db.scalar(
        select(func.count(ContestSubmission.id)).where(
            ContestSubmission.contest_id == contest.id, ContestSubmission.user_id == user.id,
        )
    ) or 0
    return {"registered": registered, "rating": rating, "submissions": submissions}


@router.post("/{slug}/register", status_code=status.HTTP_204_NO_CONTENT)
def register(slug: str, user: CurrentUser, db: DB) -> None:
    contest = find_contest(db, slug)
    if contest.publication_status != "PUBLISHED":
        raise HTTPException(status_code=409, detail="Contest registration is unavailable")
    if datetime.now(timezone.utc) >= aware(contest.starts_at):
        raise HTTPException(status_code=409, detail="Registration has closed")
    exists = db.scalar(
        select(ContestRegistration.id).where(
            ContestRegistration.contest_id == contest.id, ContestRegistration.user_id == user.id,
        )
    )
    if exists is not None:
        return
    db.add(ContestRegistration(contest_id=contest.id, user_id=user.id))
    try:
        db.commit()
        invalidate_public("contest")
    except IntegrityError:
        db.rollback()
        if db.scalar(select(ContestRegistration.id).where(
            ContestRegistration.contest_id == contest.id, ContestRegistration.user_id == user.id,
        )) is None:
            raise


@router.post(
    "/{slug}/problems/{problem_slug}/submissions",
    response_model=SubmissionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit(
    slug: str, problem_slug: str, payload: SubmissionCreate,
    user: CurrentUser, db: DB, enqueue: Enqueuer,
) -> Submission:
    contest = find_contest(db, slug)
    now = datetime.now(timezone.utc)
    if contest.publication_status != "PUBLISHED":
        raise HTTPException(status_code=409, detail="Contest is unavailable")
    if not (aware(contest.starts_at) <= now < aware(contest.ends_at)):
        raise HTTPException(status_code=409, detail="Contest is not active")
    registered = db.scalar(
        select(ContestRegistration.id).where(
            ContestRegistration.contest_id == contest.id, ContestRegistration.user_id == user.id,
        )
    )
    if registered is None:
        raise HTTPException(status_code=403, detail="Contest registration is required")
    contest_problem = db.get(ContestProblem, (contest.id, problem_slug))
    problem = db.get(Problem, problem_slug)
    if contest_problem is None or problem is None:
        raise HTTPException(status_code=404, detail="Contest problem not found")
    if payload.language not in {starter.language for starter in problem.starters}:
        raise HTTPException(status_code=422, detail="Language is unavailable for this problem")
    submission = Submission(
        id=str(uuid4()), user_id=user.id, contest_id=contest.id, problem_slug=problem_slug,
        language=payload.language, source_code=payload.source_code, mode="SUBMIT",
    )
    db.add(submission)
    db.flush()
    db.add(ContestSubmission(
        contest_id=contest.id, user_id=user.id, problem_slug=problem_slug,
        submission_id=submission.id, submitted_at=now,
    ))
    award_achievement(db, user.id, "first-contest")
    db.commit()
    invalidate_public("contest", "leaderboard")
    db.refresh(submission)
    try:
        enqueue(submission.id)
    except Exception:
        submission.status = "SYSTEM_ERROR"
        submission.verdict = "SYSTEM_ERROR"
        submission.output = "The judge queue is unavailable."
        db.commit()
        invalidate_public("contest", "leaderboard")
        db.refresh(submission)
    return submission


@router.get("/{slug}/leaderboard", response_model=list[ContestStanding])
def contest_leaderboard(slug: str, db: DB) -> list[dict]:
    contest = find_contest(db, slug)
    key = cache_key("contest", "leaderboard", slug)
    cached = get_public(key)
    if cached is not None:
        return cached
    standings = calculate_standings(db, contest)
    set_public(key, standings)
    return standings


@router.post("/{slug}/finalize", status_code=status.HTTP_204_NO_CONTENT)
def finalize(slug: str, db: DB, admin: Annotated[User, Depends(require_admin)]) -> None:
    contest = db.scalar(select(Contest).where(Contest.slug == slug).with_for_update())
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    if datetime.now(timezone.utc) < aware(contest.ends_at):
        raise HTTPException(status_code=409, detail="Contest is still active")
    if not contest.is_rated:
        contest.publication_status = "FINALIZED"
        db.commit()
        invalidate_public("contest")
        return
    if db.scalar(select(ContestRating.id).where(ContestRating.contest_id == contest.id)) is not None:
        return
    standings = calculate_standings(db, contest)
    size = len(standings)
    for row in standings:
        participant = db.scalar(select(User).where(User.username == row["username"]))
        previous = db.scalar(
            select(ContestRating.rating_after)
            .join(Contest, Contest.id == ContestRating.contest_id)
            .where(ContestRating.user_id == participant.id, Contest.ends_at < contest.ends_at)
            .order_by(Contest.ends_at.desc())
            .limit(1)
        ) or 1200
        delta = (size + 1 - 2 * row["position"]) * 16 if size > 1 else 0
        db.add(ContestRating(
            contest_id=contest.id, user_id=participant.id, rating_before=previous,
            rating_after=max(0, previous + delta), position=row["position"],
        ))
    contest.publication_status = "FINALIZED"
    db.commit()
    invalidate_public("contest", "leaderboard")


@router.post("", response_model=ContestCreated, status_code=status.HTTP_201_CREATED)
def create_contest(
    payload: ContestCreate, db: DB, admin: Annotated[User, Depends(require_admin)],
) -> dict:
    if db.scalar(select(Contest.id).where(Contest.slug == payload.slug)) is not None:
        raise HTTPException(status_code=409, detail="Contest slug already exists")
    for problem_slug in payload.problems:
        if db.get(Problem, problem_slug) is None:
            raise HTTPException(status_code=422, detail=f"Problem does not exist: {problem_slug}")
    contest = Contest(**payload.model_dump(exclude={"problems"}))
    db.add(contest)
    db.flush()
    for position, problem_slug in enumerate(payload.problems, 1):
        db.add(ContestProblem(contest_id=contest.id, problem_slug=problem_slug, position=position))
    db.commit()
    invalidate_public("contest")
    return {"slug": contest.slug}


def find_contest(db: Session, slug: str) -> Contest:
    contest = db.scalar(select(Contest).where(Contest.slug == slug))
    if contest is None or contest.publication_status == "DRAFT":
        raise HTTPException(status_code=404, detail="Contest not found")
    return contest


def calculate_standings(db: Session, contest: Contest) -> list[dict]:
    problem_points = dict(db.execute(
        select(ContestProblem.problem_slug, ContestProblem.points)
        .where(ContestProblem.contest_id == contest.id)
    ).all())
    registrations = db.execute(
        select(ContestRegistration, User, Profile)
        .join(User, User.id == ContestRegistration.user_id)
        .join(Profile, Profile.user_id == User.id)
        .where(ContestRegistration.contest_id == contest.id)
    ).all()
    attempts = db.execute(
        select(ContestSubmission, Submission)
        .join(Submission, Submission.id == ContestSubmission.submission_id)
        .where(ContestSubmission.contest_id == contest.id)
        .order_by(ContestSubmission.submitted_at)
    ).all()
    standings = []
    for registration, user, profile in registrations:
        del registration
        user_attempts = [row for row in attempts if row.ContestSubmission.user_id == user.id]
        score = penalty = solved = 0
        for problem_slug, points in problem_points.items():
            wrong = 0
            for row in [entry for entry in user_attempts if entry.ContestSubmission.problem_slug == problem_slug]:
                if row.Submission.verdict == "ACCEPTED":
                    score += points
                    solved += 1
                    elapsed = max(0, int(
                        (aware(row.ContestSubmission.submitted_at) - aware(contest.starts_at)).total_seconds()
                    ))
                    penalty += elapsed + wrong * 1200
                    break
                if row.Submission.status == "FINISHED":
                    wrong += 1
        standings.append({
            "username": user.username, "display_name": profile.display_name,
            "score": score, "solved": solved, "penalty_seconds": penalty,
        })
    standings.sort(key=lambda row: (-row["score"], row["penalty_seconds"], row["username"]))
    for position, row in enumerate(standings, 1):
        row["position"] = position
    return standings


def contest_status(contest: Contest, now: datetime) -> str:
    if contest.publication_status in {"CANCELLED", "FINALIZED"}:
        return contest.publication_status
    if now < aware(contest.starts_at):
        return "UPCOMING"
    if now < aware(contest.ends_at):
        return "ACTIVE"
    return "FINISHED"
