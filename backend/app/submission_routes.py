from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .access_control import can_access
from .auth import CurrentUser
from .main_dependencies import get_db
from .judge_client import Enqueuer
from .models import Problem, Submission
from .schemas_submissions import SubmissionCreate, SubmissionRead

router = APIRouter(tags=["submissions"])
DB = Annotated[Session, Depends(get_db)]


@router.post("/problems/{slug}/submissions", response_model=SubmissionRead, status_code=status.HTTP_202_ACCEPTED)
def create_submission(slug: str, payload: SubmissionCreate, user: CurrentUser, db: DB, enqueue: Enqueuer) -> Submission:
    problem = db.get(Problem, slug)
    if problem is None or problem.status != "PUBLISHED" or not can_access(db, problem, "problem", user):
        raise HTTPException(status_code=404, detail="Problem not found")
    languages = {starter.language for starter in problem.starters}
    if languages and payload.language not in languages:
        raise HTTPException(status_code=422, detail="Language is unavailable for this problem")
    submission = Submission(
        id=str(uuid4()), user_id=user.id, problem_slug=slug, language=payload.language,
        source_code=payload.source_code, mode=payload.mode,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    try:
        enqueue(submission.id)
    except Exception:
        submission.status = "SYSTEM_ERROR"
        submission.verdict = "SYSTEM_ERROR"
        submission.output = "The judge queue is unavailable. Please try again."
        db.commit()
        db.refresh(submission)
    return submission


@router.get("/submissions", response_model=list[SubmissionRead])
def submission_history(
    user: CurrentUser, db: DB, limit: Annotated[int, Query(ge=1, le=100)] = 25,
    problem_slug: Annotated[str | None, Query(max_length=100)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Submission]:
    query = select(Submission).where(Submission.user_id == user.id)
    if problem_slug:
        query = query.where(Submission.problem_slug == problem_slug)
    return list(db.scalars(query.order_by(Submission.created_at.desc(), Submission.id.desc()).limit(limit).offset(offset)))


@router.get("/submissions/{submission_id}", response_model=SubmissionRead)
def submission_detail(submission_id: str, user: CurrentUser, db: DB) -> Submission:
    item = db.get(Submission, submission_id)
    if item is None or (item.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Submission not found")
    return item


@router.post("/submissions/{submission_id}/cancel", response_model=SubmissionRead)
def cancel_submission(submission_id: str, user: CurrentUser, db: DB) -> Submission:
    item = db.scalar(select(Submission).where(Submission.id == submission_id).with_for_update())
    if item is None or (item.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Submission not found")
    if item.status in {"FINISHED", "SYSTEM_ERROR", "CANCELLED"}:
        raise HTTPException(status_code=409, detail="Submission is already final")
    now = datetime.now(timezone.utc)
    item.cancel_requested_at = now
    if item.status == "QUEUED":
        item.status = "CANCELLED"
        item.verdict = "CANCELLED"
        item.output = "Submission cancelled before execution."
        item.finished_at = now
    db.commit()
    db.refresh(item)
    return item
