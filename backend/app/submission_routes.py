from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import CurrentUser, require_admin
from .main_dependencies import get_db
from .judge_client import Enqueuer
from .models import Problem, StarterCode, Submission, TestCase, User
from .schemas_submissions import ProblemAdminWrite, SubmissionCreate, SubmissionRead

router = APIRouter(tags=["submissions"])
DB = Annotated[Session, Depends(get_db)]


@router.post("/problems/{slug}/submissions", response_model=SubmissionRead, status_code=status.HTTP_202_ACCEPTED)
def create_submission(slug: str, payload: SubmissionCreate, user: CurrentUser, db: DB, enqueue: Enqueuer) -> Submission:
    problem = db.get(Problem, slug)
    if problem is None:
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
) -> list[Submission]:
    query = select(Submission).where(Submission.user_id == user.id)
    if problem_slug:
        query = query.where(Submission.problem_slug == problem_slug)
    return list(db.scalars(query.order_by(Submission.created_at.desc()).limit(limit)))


@router.get("/submissions/{submission_id}", response_model=SubmissionRead)
def submission_detail(submission_id: str, user: CurrentUser, db: DB) -> Submission:
    item = db.get(Submission, submission_id)
    if item is None or (item.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Submission not found")
    return item


@router.put("/admin/problems/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def upsert_problem(
    slug: str, payload: ProblemAdminWrite, db: DB,
    admin: Annotated[User, Depends(require_admin)],
) -> None:
    values = payload.model_dump(exclude={"test_cases"})
    problem = db.get(Problem, slug)
    if problem is None:
        problem = Problem(slug=slug, starters=[], **values)
        db.add(problem)
    else:
        for key, value in values.items():
            setattr(problem, key, value)
        problem.test_cases.clear()
    problem.test_cases.extend(TestCase(**case.model_dump()) for case in payload.test_cases)
    db.commit()
