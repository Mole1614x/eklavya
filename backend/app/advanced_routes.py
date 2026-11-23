from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .access_control import audience_filter, can_access, prevent_unconfirmed_inline_change, require_publishable, replace_students, student_ids, validate_students
from .advanced_evaluators import EXCEL_FUNCTIONS, TABLEAU_FUNCTIONS, ExpressionError, equivalent, evaluate_excel, evaluate_tableau, validate_tableau
from .auth import CurrentUser, require_admin
from .config import settings
from .dataset_lab import DatasetError, parse_dataset, profile_dataset, rows_to_csv, transform_rows, validate_filename, validate_xlsx_archive
from .main_dependencies import get_db
from .judge_client import DatasetPracticeEnqueuer, Enqueuer
from .models import (
    Assessment, AssessmentAnswer, AssessmentAssignment, AssessmentAttempt, AssessmentGroupAssignment, AssessmentQuestion,
    AssessmentResult, AuditLog, DatasetPracticeRun, LearnerGroup, LearnerGroupMember, MultiToolProgress, PracticeDataset, Problem, Submission, TestCase, User,
)
from .schemas_advanced import (
    AnalyticsRead, AnswerWrite, AssessmentRead, AssessmentStatusWrite, AssessmentTemplateCreate, AssessmentWrite, AttemptRead,
    DatasetPracticeRead, DatasetPracticeWrite, DatasetRead, DatasetTransform, DatasetUpload, EvaluationRead, ExpressionSubmission, LearnerGroupWrite, MultiToolSubmission, WorkbookSubmission,
)
from .schemas_submissions import SubmissionCreate, SubmissionRead

router = APIRouter(prefix="/advanced", tags=["advanced-practice"])
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]

TEMPLATES = {
    "python-developer": {"title": "Python Developer", "subjects": ["Python", "DSA", "SQL"], "duration_minutes": 90},
    "data-analyst": {"title": "Data Analyst", "subjects": ["SQL", "Pandas", "Statistics", "Excel", "Tableau"], "duration_minutes": 120},
    "data-engineer": {"title": "Data Engineer", "subjects": ["Python", "SQL", "PySpark", "Linux", "ETL"], "duration_minutes": 120},
    "ml-engineer": {"title": "ML Engineer", "subjects": ["Python", "NumPy", "Statistics", "Machine Learning", "Model evaluation"], "duration_minutes": 120},
    "software-developer": {"title": "Software Developer", "subjects": ["DSA", "Programming", "Problem solving", "SQL"], "duration_minutes": 90},
}
TEMPLATE_CATEGORIES = {
    "python-developer": ["foundations", "code", "data"], "data-analyst": ["data", "statistics", "excel", "tableau"],
    "data-engineer": ["data", "big-data", "linux"], "ml-engineer": ["foundations", "statistics", "ai"],
    "software-developer": ["foundations", "code", "data"],
}

MULTI_TOOL_CHALLENGES = [{
    "key": "sales-by-region", "title": "Total sales by region",
    "description": "Aggregate Orders by Region and return the total Sales for each region.",
    "objective": "Grouping and aggregation semantics across analytical tools",
    "technologies": ["SQL", "PANDAS", "PYSPARK", "EXCEL", "TABLEAU"],
    "notes": "Results are compared as unordered region/total pairs; null region values are excluded.",
}]


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def audit(db: Session, request: Request, actor: User, action: str, target: str, target_id: str, details: dict | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, target_type=target, target_id=target_id,
                    details=details or {}, ip_address=request.client.host if request.client else None))


def assessment_read(db: Session, item: Assessment) -> dict[str, Any]:
    questions = db.execute(
        select(AssessmentQuestion, Problem).join(Problem, Problem.slug == AssessmentQuestion.problem_slug)
        .where(AssessmentQuestion.assessment_id == item.id).order_by(AssessmentQuestion.position)
    ).all()
    assigned_users = set(db.scalars(select(AssessmentAssignment.user_id).where(AssessmentAssignment.assessment_id == item.id)))
    assigned_users.update(db.scalars(select(LearnerGroupMember.user_id).join(
        AssessmentGroupAssignment, AssessmentGroupAssignment.group_id == LearnerGroupMember.group_id,
    ).where(AssessmentGroupAssignment.assessment_id == item.id)))
    return {
        "id": item.id, "title": item.title, "description": item.description, "instructions": item.instructions,
        "assessment_type": item.assessment_type, "duration_minutes": item.duration_minutes,
        "opens_at": item.opens_at, "closes_at": item.closes_at, "max_attempts": item.max_attempts,
        "penalty_percent": item.penalty_percent, "release_results": item.release_results,
        "status": item.status, "template_key": item.template_key, "access_scope": item.access_scope,
        "assigned_user_ids": student_ids(db, "assessment", item.id),
        "assigned_group_ids": sorted(db.scalars(select(AssessmentGroupAssignment.group_id).where(AssessmentGroupAssignment.assessment_id == item.id))),
        "questions": [{"problem_slug": question.problem_slug, "title": problem.title,
                       "difficulty": problem.difficulty, "position": question.position, "points": question.points}
                       | {"languages": [starter.language for starter in problem.starters], "format": problem.format}
                      for question, problem in questions],
        "assigned_count": len(assigned_users),
        "attempt_count": db.scalar(select(func.count(AssessmentAttempt.id)).where(AssessmentAttempt.assessment_id == item.id)) or 0,
    }


@router.get("/templates")
def templates() -> list[dict[str, Any]]:
    return [{"key": key, **value} for key, value in TEMPLATES.items()]


@router.get("/admin/groups")
def learner_groups(db: DB, admin: Admin) -> list[dict[str, Any]]:
    del admin
    groups = list(db.scalars(select(LearnerGroup).order_by(LearnerGroup.name)))
    return [{"id": group.id, "name": group.name,
             "user_ids": list(db.scalars(select(LearnerGroupMember.user_id).where(LearnerGroupMember.group_id == group.id))),
             "created_at": group.created_at} for group in groups]


@router.post("/admin/groups", status_code=status.HTTP_201_CREATED)
def create_learner_group(payload: LearnerGroupWrite, request: Request, db: DB, admin: Admin) -> dict[str, Any]:
    if db.scalar(select(LearnerGroup).where(func.lower(LearnerGroup.name) == payload.name.strip().lower())):
        raise HTTPException(status_code=409, detail="A learner group with this name already exists")
    invalid = [user_id for user_id in payload.user_ids if db.get(User, user_id) is None]
    if invalid: raise HTTPException(status_code=422, detail="One or more group members do not exist")
    group = LearnerGroup(id=str(uuid4()), name=payload.name.strip(), created_by=admin.id); db.add(group); db.flush()
    db.add_all(LearnerGroupMember(group_id=group.id, user_id=user_id) for user_id in sorted(set(payload.user_ids)))
    audit(db, request, admin, "learner_group.create", "learner_group", group.id, {"member_count": len(set(payload.user_ids))})
    db.commit()
    return {"id": group.id, "name": group.name, "user_ids": sorted(set(payload.user_ids)), "created_at": group.created_at}


@router.get("/admin/assessments", response_model=list[AssessmentRead])
def admin_assessments(db: DB, admin: Admin, limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0) -> list[dict]:
    del admin
    return [assessment_read(db, item) for item in db.scalars(select(Assessment).order_by(Assessment.created_at.desc()).limit(limit).offset(offset))]


@router.post("/admin/assessments", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
def create_assessment(payload: AssessmentWrite, request: Request, db: DB, admin: Admin) -> dict:
    if payload.status == "PUBLISHED" and payload.access_scope == "SELECTED" and not (payload.assigned_user_ids or payload.assigned_group_ids):
        raise HTTPException(status_code=409, detail="Assign at least one student or group before publishing")
    item = Assessment(id=str(uuid4()), created_by=admin.id, **payload.model_dump(exclude={"questions", "assigned_user_ids", "assigned_group_ids"}))
    db.add(item)
    _replace_assessment_children(db, item, payload)
    if item.status == "PUBLISHED": require_publishable(db, item, "assessment")
    audit(db, request, admin, "assessment.create", "assessment", item.id, {"status": item.status})
    db.commit()
    return assessment_read(db, item)


@router.post("/admin/assessments/from-template/{template_key}", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
def create_assessment_from_template(template_key: str, payload: AssessmentTemplateCreate, request: Request, db: DB, admin: Admin) -> dict:
    template = TEMPLATES.get(template_key)
    if template is None: raise HTTPException(status_code=404, detail="Assessment template not found")
    if payload.question_slugs:
        slugs = payload.question_slugs
    else:
        filters = [Problem.status == "PUBLISHED", Problem.category.in_(TEMPLATE_CATEGORIES[template_key])]
        if payload.difficulty: filters.append(Problem.difficulty == payload.difficulty)
        slugs = list(db.scalars(select(Problem.slug).where(*filters).order_by(Problem.category, Problem.difficulty, Problem.title).limit(10)))
    if not slugs: raise HTTPException(status_code=409, detail="No published questions match this template configuration")
    definition = AssessmentWrite(
        title=payload.title or f"{template['title']} Assessment", description=f"Role template: {template['title']}",
        instructions="Complete every question before the server-authoritative timer expires.", assessment_type="MIXED",
        duration_minutes=payload.duration_minutes or template["duration_minutes"], opens_at=payload.opens_at,
        closes_at=payload.closes_at, release_results=payload.release_results, status="DRAFT", template_key=template_key,
        questions=[{"problem_slug": slug, "points": 100} for slug in slugs],
        assigned_user_ids=payload.assigned_user_ids, assigned_group_ids=payload.assigned_group_ids,
        access_scope=payload.access_scope,
    )
    return create_assessment(definition, request, db, admin)


@router.put("/admin/assessments/{assessment_id}", response_model=AssessmentRead)
def update_assessment(assessment_id: str, payload: AssessmentWrite, request: Request, db: DB, admin: Admin) -> dict:
    item = db.get(Assessment, assessment_id)
    if item is None: raise HTTPException(status_code=404, detail="Assessment not found")
    prevent_unconfirmed_inline_change(db, item, "assessment", payload.model_fields_set, payload.access_scope, payload.assigned_user_ids)
    if db.scalar(select(func.count(AssessmentAttempt.id)).where(AssessmentAttempt.assessment_id == item.id)):
        raise HTTPException(status_code=409, detail="An assessment with attempts cannot have its questions or timing replaced")
    for key, value in payload.model_dump(exclude={"questions", "assigned_user_ids", "assigned_group_ids"}).items(): setattr(item, key, value)
    db.execute(delete(AssessmentQuestion).where(AssessmentQuestion.assessment_id == item.id))
    db.execute(delete(AssessmentAssignment).where(AssessmentAssignment.assessment_id == item.id))
    db.execute(delete(AssessmentGroupAssignment).where(AssessmentGroupAssignment.assessment_id == item.id))
    _replace_assessment_children(db, item, payload)
    if item.status == "PUBLISHED": require_publishable(db, item, "assessment")
    audit(db, request, admin, "assessment.update", "assessment", item.id)
    db.commit()
    return assessment_read(db, item)


def _replace_assessment_children(db: Session, item: Assessment, payload: AssessmentWrite) -> None:
    missing = [question.problem_slug for question in payload.questions if db.get(Problem, question.problem_slug) is None]
    if missing: raise HTTPException(status_code=422, detail=f"Unknown problem(s): {', '.join(missing)}")
    validate_students(db, payload.assigned_user_ids)
    invalid_groups = [group_id for group_id in payload.assigned_group_ids if db.get(LearnerGroup, group_id) is None]
    if invalid_groups: raise HTTPException(status_code=422, detail="One or more assigned groups do not exist")
    db.add_all(AssessmentQuestion(assessment_id=item.id, problem_slug=question.problem_slug, position=index, points=question.points)
               for index, question in enumerate(payload.questions))
    db.add_all(AssessmentAssignment(assessment_id=item.id, user_id=user_id) for user_id in payload.assigned_user_ids)
    db.add_all(AssessmentGroupAssignment(assessment_id=item.id, group_id=group_id) for group_id in payload.assigned_group_ids)
    db.flush()


@router.patch("/admin/assessments/{assessment_id}/status", response_model=AssessmentRead)
def assessment_status(assessment_id: str, payload: AssessmentStatusWrite, request: Request, db: DB, admin: Admin) -> dict:
    item = db.get(Assessment, assessment_id)
    if item is None: raise HTTPException(status_code=404, detail="Assessment not found")
    if payload.status == "PUBLISHED": require_publishable(db, item, "assessment")
    item.status = payload.status
    audit(db, request, admin, "assessment.status", "assessment", item.id, {"status": payload.status, "reason": payload.reason})
    db.commit()
    return assessment_read(db, item)


@router.get("/admin/assessments/{assessment_id}/analytics")
def assessment_analytics(assessment_id: str, db: DB, admin: Admin) -> dict[str, Any]:
    del admin
    item = db.get(Assessment, assessment_id)
    if item is None: raise HTTPException(status_code=404, detail="Assessment not found")
    attempts = list(db.scalars(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id == item.id)))
    completed = [attempt for attempt in attempts if attempt.status != "IN_PROGRESS"]
    return {"assessment_id": item.id, "assigned": db.scalar(select(func.count(AssessmentAssignment.id)).where(AssessmentAssignment.assessment_id == item.id)) or 0,
            "started": len(attempts), "completed": len(completed),
            "average_score": round(sum(attempt.score for attempt in completed) / len(completed), 2) if completed else None,
            "average_percent": round(sum((attempt.score / attempt.max_score * 100) if attempt.max_score else 0 for attempt in completed) / len(completed), 2) if completed else None}


@router.get("/admin/assessments/{assessment_id}/export")
def export_assessment(assessment_id: str, db: DB, admin: Admin, format: LiteralFormat = "csv"):
    del admin
    item = db.get(Assessment, assessment_id)
    if item is None: raise HTTPException(status_code=404, detail="Assessment not found")
    rows = db.execute(select(AssessmentAttempt, User).join(User, User.id == AssessmentAttempt.user_id)
                      .where(AssessmentAttempt.assessment_id == item.id).order_by(User.username, AssessmentAttempt.attempt_number)).all()
    headings = ["username", "attempt", "status", "started_at", "finalized_at", "score", "max_score"]
    values = [[user.username, attempt.attempt_number, attempt.status, attempt.started_at.isoformat(),
               attempt.finalized_at.isoformat() if attempt.finalized_at else "", attempt.score, attempt.max_score] for attempt, user in rows]
    if format == "xlsx":
        try:
            from openpyxl import Workbook
        except ImportError as error: raise HTTPException(status_code=503, detail="XLSX export support is unavailable") from error
        workbook = Workbook(write_only=True); sheet = workbook.create_sheet("Results"); sheet.append(headings)
        for row in values: sheet.append(row)
        output = io.BytesIO(); workbook.save(output)
        return Response(output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="assessment-{assessment_id}.xlsx"'})
    output = io.StringIO(newline=""); writer = csv.writer(output); writer.writerow(headings); writer.writerows(values)
    return Response(output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="assessment-{assessment_id}.csv"'})


LiteralFormat = Annotated[str, Query(pattern="^(csv|xlsx)$")]


@router.get("/assessments", response_model=list[AssessmentRead])
def my_assessments(db: DB, user: CurrentUser) -> list[dict]:
    items = db.scalars(select(Assessment).where(
        Assessment.status == "PUBLISHED", audience_filter(Assessment, "assessment", user)
    ).order_by(Assessment.opens_at.desc())).all()
    # The list shows counts, not question text or slugs before an attempt starts.
    result = [assessment_read(db, item) for item in items]
    for summary in result:
        summary["questions"] = [{"position": index} for index, _ in enumerate(summary["questions"])]
    return result


@router.post("/assessments/{assessment_id}/start", response_model=AttemptRead, status_code=status.HTTP_201_CREATED)
def start_assessment(assessment_id: str, db: DB, user: CurrentUser) -> dict:
    now = datetime.now(timezone.utc)
    item = db.get(Assessment, assessment_id)
    if item is None or item.status != "PUBLISHED" or not can_access(db, item, "assessment", user):
        raise HTTPException(status_code=404, detail="Assessment not found")
    if now < aware(item.opens_at) or now >= aware(item.closes_at): raise HTTPException(status_code=409, detail="Assessment is outside its permitted window")
    active = db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id == item.id,
                                                        AssessmentAttempt.user_id == user.id,
                                                        AssessmentAttempt.status == "IN_PROGRESS").with_for_update())
    if active is not None:
        if now < aware(active.deadline_at): return attempt_read(db, active, item, user)
        finalize_attempt(db, active, expired=True)
    count = db.scalar(select(func.count(AssessmentAttempt.id)).where(AssessmentAttempt.assessment_id == item.id,
                                                                      AssessmentAttempt.user_id == user.id)) or 0
    if count >= item.max_attempts: raise HTTPException(status_code=409, detail="Maximum assessment attempts reached")
    deadline = min(now + timedelta(minutes=item.duration_minutes), aware(item.closes_at))
    attempt = AssessmentAttempt(id=str(uuid4()), assessment_id=item.id, user_id=user.id,
                                attempt_number=count + 1, started_at=now, deadline_at=deadline)
    db.add(attempt)
    try: db.commit()
    except IntegrityError as error:
        db.rollback(); raise HTTPException(status_code=409, detail="A concurrent attempt was already created") from error
    return attempt_read(db, attempt, item, user)


@router.get("/assessments/attempts/{attempt_id}", response_model=AttemptRead)
def get_attempt(attempt_id: str, db: DB, user: CurrentUser) -> dict:
    attempt = db.get(AssessmentAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id: raise HTTPException(status_code=404, detail="Assessment attempt not found")
    item = db.get(Assessment, attempt.assessment_id)
    if attempt.status == "IN_PROGRESS" and datetime.now(timezone.utc) >= aware(attempt.deadline_at):
        finalize_attempt(db, attempt, expired=True); db.commit()
    return attempt_read(db, attempt, item, user)


@router.put("/assessments/attempts/{attempt_id}/answers", response_model=AttemptRead)
def autosave_answer(attempt_id: str, payload: AnswerWrite, db: DB, user: CurrentUser) -> dict:
    attempt = db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id).with_for_update())
    if attempt is None or attempt.user_id != user.id: raise HTTPException(status_code=404, detail="Assessment attempt not found")
    now = datetime.now(timezone.utc)
    if attempt.status != "IN_PROGRESS": raise HTTPException(status_code=409, detail="Assessment attempt is already finalized")
    if now >= aware(attempt.deadline_at):
        finalize_attempt(db, attempt, expired=True); db.commit(); raise HTTPException(status_code=409, detail="Assessment time expired and the attempt was finalized")
    question = db.get(AssessmentQuestion, (attempt.assessment_id, payload.problem_slug))
    if question is None: raise HTTPException(status_code=422, detail="Problem is not part of this assessment")
    if payload.submission_id:
        submission = db.get(Submission, payload.submission_id)
        if submission is None or submission.user_id != user.id or submission.problem_slug != payload.problem_slug:
            raise HTTPException(status_code=422, detail="Submission does not belong to this learner and assessment problem")
    answer = db.scalar(select(AssessmentAnswer).where(AssessmentAnswer.attempt_id == attempt.id,
                                                       AssessmentAnswer.problem_slug == payload.problem_slug))
    if answer is None:
        answer = AssessmentAnswer(attempt_id=attempt.id, **payload.model_dump()); db.add(answer)
    else:
        for key, value in payload.model_dump().items(): setattr(answer, key, value)
        answer.saved_at = now
    db.commit()
    return attempt_read(db, attempt, db.get(Assessment, attempt.assessment_id), user)


@router.post("/assessments/attempts/{attempt_id}/questions/{problem_slug}/submissions", response_model=SubmissionRead, status_code=status.HTTP_202_ACCEPTED)
def assessment_submission(attempt_id: str, problem_slug: str, payload: SubmissionCreate, db: DB, user: CurrentUser, enqueue: Enqueuer) -> Submission:
    attempt = db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id).with_for_update())
    if attempt is None or attempt.user_id != user.id: raise HTTPException(status_code=404, detail="Assessment attempt not found")
    if attempt.status != "IN_PROGRESS": raise HTTPException(status_code=409, detail="Assessment attempt is already finalized")
    if datetime.now(timezone.utc) >= aware(attempt.deadline_at):
        finalize_attempt(db, attempt, expired=True); db.commit(); raise HTTPException(status_code=409, detail="Assessment time expired and the attempt was finalized")
    question = db.get(AssessmentQuestion, (attempt.assessment_id, problem_slug))
    problem = db.get(Problem, problem_slug)
    if question is None or problem is None: raise HTTPException(status_code=404, detail="Assessment question not found")
    languages = {starter.language for starter in problem.starters}
    if languages and payload.language not in languages: raise HTTPException(status_code=422, detail="Language is unavailable for this problem")
    submission = Submission(id=str(uuid4()), user_id=user.id, problem_slug=problem_slug, language=payload.language,
                            source_code=payload.source_code, mode=payload.mode)
    db.add(submission); db.flush()
    answer = db.scalar(select(AssessmentAnswer).where(AssessmentAnswer.attempt_id == attempt.id,
                                                       AssessmentAnswer.problem_slug == problem_slug))
    if answer is None:
        answer = AssessmentAnswer(attempt_id=attempt.id, problem_slug=problem_slug, answer=payload.source_code,
                                  language=payload.language, submission_id=submission.id); db.add(answer)
    else:
        answer.answer, answer.language, answer.submission_id = payload.source_code, payload.language, submission.id
        answer.saved_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(submission)
    try: enqueue(submission.id)
    except Exception:
        submission.status, submission.verdict = "SYSTEM_ERROR", "SYSTEM_ERROR"
        submission.output, submission.finished_at = "The judge queue is unavailable. Please try again.", datetime.now(timezone.utc)
        db.commit(); db.refresh(submission)
    return submission


@router.post("/assessments/attempts/{attempt_id}/submit", response_model=AttemptRead)
def submit_attempt(attempt_id: str, db: DB, user: CurrentUser) -> dict:
    attempt = db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id).with_for_update())
    if attempt is None or attempt.user_id != user.id: raise HTTPException(status_code=404, detail="Assessment attempt not found")
    if attempt.status == "IN_PROGRESS":
        expired = datetime.now(timezone.utc) >= aware(attempt.deadline_at)
        if not expired:
            pending = db.scalar(select(func.count(Submission.id)).join(AssessmentAnswer, AssessmentAnswer.submission_id == Submission.id)
                                .where(AssessmentAnswer.attempt_id == attempt.id, Submission.status.in_(["QUEUED", "RUNNING"]))) or 0
            if pending: raise HTTPException(status_code=409, detail="Wait for assessment judge submissions to finish before finalizing")
        finalize_attempt(db, attempt, expired=expired)
    db.commit()
    return attempt_read(db, attempt, db.get(Assessment, attempt.assessment_id), user)


def finalize_attempt(db: Session, attempt: AssessmentAttempt, expired: bool) -> None:
    if attempt.status != "IN_PROGRESS": return
    questions = list(db.scalars(select(AssessmentQuestion).where(AssessmentQuestion.assessment_id == attempt.assessment_id)))
    answers = {answer.problem_slug: answer for answer in db.scalars(select(AssessmentAnswer).where(AssessmentAnswer.attempt_id == attempt.id))}
    score = 0.0; correct = 0; breakdown = []
    for question in questions:
        answer = answers.get(question.problem_slug); passed = False
        if answer and answer.submission_id:
            submission = db.get(Submission, answer.submission_id)
            passed = bool(submission and submission.user_id == attempt.user_id and submission.problem_slug == question.problem_slug and submission.verdict == "ACCEPTED")
        elif answer:
            expected_case = db.scalar(select(TestCase).where(TestCase.problem_slug == question.problem_slug).order_by(TestCase.is_hidden.desc(), TestCase.position))
            if expected_case:
                expected = expected_case.expected_output.strip().strip('"')
                passed = answer.answer.strip() == expected
        if passed: score += question.points; correct += 1
        breakdown.append({"problem_slug": question.problem_slug, "passed": passed, "points_awarded": question.points if passed else 0})
    item = db.get(Assessment, attempt.assessment_id)
    if item.penalty_percent and not expired:
        score = max(0, score - sum(question.points for question in questions if question.problem_slug in answers and not next(entry["passed"] for entry in breakdown if entry["problem_slug"] == question.problem_slug)) * item.penalty_percent / 100)
    attempt.status = "EXPIRED" if expired else "SUBMITTED"; attempt.finalized_at = datetime.now(timezone.utc)
    attempt.score = score; attempt.max_score = sum(question.points for question in questions)
    result = db.get(AssessmentResult, attempt.id)
    if result is None: db.add(AssessmentResult(attempt_id=attempt.id, correct_answers=correct, total_answers=len(questions), breakdown=breakdown,
                                                released_at=datetime.now(timezone.utc) if item.release_results else None))


def attempt_read(db: Session, attempt: AssessmentAttempt, item: Assessment, user: User) -> dict[str, Any]:
    questions = assessment_read(db, item)["questions"]
    answers = list(db.scalars(select(AssessmentAnswer).where(AssessmentAnswer.attempt_id == attempt.id)))
    released = item.release_results and attempt.status != "IN_PROGRESS"
    return {"id": attempt.id, "assessment_id": item.id, "assessment_title": item.title,
            "attempt_number": attempt.attempt_number, "status": attempt.status, "started_at": attempt.started_at,
            "deadline_at": attempt.deadline_at, "server_time": datetime.now(timezone.utc), "finalized_at": attempt.finalized_at,
            "score": attempt.score if released else None, "max_score": attempt.max_score if released else None,
            "questions": questions, "answers": [{"problem_slug": answer.problem_slug, "answer": answer.answer,
                                                   "language": answer.language, "submission_id": answer.submission_id,
                                                   "saved_at": answer.saved_at} for answer in answers]}


def dataset_read(item: PracticeDataset, user: User) -> dict[str, Any]:
    return {"id": item.id, "title": item.title, "description": item.description, "category": item.category,
            "difficulty": item.difficulty, "format": item.format, "original_filename": item.original_filename,
            "size_bytes": item.size_bytes, "status": item.status, "access_scope": item.access_scope, "version": item.version,
            "download_allowed": item.download_allowed, "column_info": item.column_info, "profile": item.profile,
            "transformations": item.transformations, "created_at": item.created_at,
            "owned_by_current_user": item.owner_user_id == user.id}


@router.post("/datasets", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
def upload_dataset(payload: DatasetUpload, request: Request, db: DB, user: CurrentUser) -> dict:
    if payload.publish and user.role != "admin": raise HTTPException(status_code=403, detail="Only administrators can publish library datasets")
    if payload.assigned_user_ids and user.role != "admin": raise HTTPException(status_code=403, detail="Only administrators can assign students")
    validate_students(db, payload.assigned_user_ids)
    if payload.publish and payload.access_scope == "SELECTED" and not payload.assigned_user_ids:
        raise HTTPException(status_code=409, detail="Assign at least one student when access is SELECTED")
    extension, dataset_format = _dataset_input(payload)
    try: content = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as error: raise HTTPException(status_code=422, detail="Dataset content is not valid base64") from error
    if not content: raise HTTPException(status_code=422, detail="Dataset is empty")
    if len(content) > settings().dataset_max_bytes: raise HTTPException(status_code=413, detail="Dataset exceeds the configured upload limit")
    owned_bytes = db.scalar(select(func.coalesce(func.sum(PracticeDataset.size_bytes), 0)).where(PracticeDataset.owner_user_id == user.id, PracticeDataset.status != "ARCHIVED")) or 0
    if owned_bytes + len(content) > settings().dataset_max_bytes * 10: raise HTTPException(status_code=413, detail="Personal dataset quota exceeded")
    try:
        rows, columns = parse_dataset(content, dataset_format); column_info, profile = profile_dataset(rows, columns)
    except DatasetError as error: raise HTTPException(status_code=422, detail=str(error)) from error
    identifier = str(uuid4()); root = settings().dataset_storage_dir / "practice" / str(user.id); root.mkdir(parents=True, exist_ok=True)
    path = root / f"{identifier}{extension}"; path.write_bytes(content); path.chmod(0o600)
    version = (db.scalar(select(func.max(PracticeDataset.version)).where(PracticeDataset.title == payload.title,
                                                                          PracticeDataset.created_by == user.id)) or 0) + 1
    item = PracticeDataset(id=identifier, owner_user_id=None if payload.publish else user.id, title=payload.title,
                           description=payload.description, category=payload.category, difficulty=payload.difficulty,
                           format=dataset_format, original_filename=payload.filename, content_type=payload.content_type,
                           size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest(), storage_path=str(path),
                           status="PUBLISHED" if payload.publish else "PRIVATE", access_scope=payload.access_scope, version=version,
                           download_allowed=payload.download_allowed, column_info=column_info, profile=profile,
                           transformations=[], created_by=user.id)
    db.add(item)
    if payload.publish and payload.assigned_user_ids:
        replace_students(db, "dataset", item.id, payload.assigned_user_ids)
    if user.role == "admin": audit(db, request, user, "dataset.practice_upload", "practice_dataset", item.id, {"status": item.status})
    db.commit()
    return dataset_read(item, user)


def _dataset_input(payload: DatasetUpload) -> tuple[str, str]:
    try: extension, dataset_format = validate_filename(payload.filename)
    except DatasetError as error: raise HTTPException(status_code=422, detail=str(error)) from error
    expected_types = {"CSV": {"text/csv", "application/csv", "application/vnd.ms-excel", "application/octet-stream"},
                      "XLSX": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
                      "JSON": {"application/json", "text/json", "application/octet-stream"},
                      "PARQUET": {"application/vnd.apache.parquet", "application/octet-stream"}}
    if payload.content_type.lower() not in expected_types[dataset_format]: raise HTTPException(status_code=422, detail="File extension and content type do not match")
    return extension, dataset_format


@router.get("/datasets/mine", response_model=list[DatasetRead])
def my_datasets(db: DB, user: CurrentUser) -> list[dict]:
    items = db.scalars(select(PracticeDataset).where(PracticeDataset.owner_user_id == user.id, PracticeDataset.status != "ARCHIVED")
                       .order_by(PracticeDataset.created_at.desc()).limit(100)).all()
    return [dataset_read(item, user) for item in items]


@router.get("/datasets/library", response_model=list[DatasetRead])
def dataset_library(db: DB, user: CurrentUser, category: Annotated[str | None, Query(max_length=32)] = None) -> list[dict]:
    filters = [PracticeDataset.status == "PUBLISHED"]
    if category: filters.append(PracticeDataset.category == category)
    items = db.scalars(select(PracticeDataset).where(
        *filters, audience_filter(PracticeDataset, "dataset", user)
    ).order_by(PracticeDataset.category, PracticeDataset.title).limit(100)).all()
    return [dataset_read(item, user) for item in items]


def own_dataset(db: Session, dataset_id: str, user: User, allow_admin: bool = True) -> PracticeDataset:
    item = db.get(PracticeDataset, dataset_id)
    if item is None or (item.owner_user_id != user.id and not (allow_admin and user.role == "admin")):
        raise HTTPException(status_code=404, detail="Dataset not found")
    return item


@router.post("/datasets/{dataset_id}/transform", response_model=DatasetRead)
def transform_dataset(dataset_id: str, payload: DatasetTransform, db: DB, user: CurrentUser) -> dict:
    item = own_dataset(db, dataset_id, user)
    if len(item.transformations) >= 50: raise HTTPException(status_code=409, detail="Dataset transformation history limit reached")
    try:
        content = Path(item.storage_path).read_bytes(); rows, columns = parse_dataset(content, item.format)
        for transform in item.transformations: rows = transform_rows(rows, **transform)
        definition = payload.model_dump(exclude_none=True); rows = transform_rows(rows, **definition)
        columns = list(rows[0]) if rows else columns; column_info, profile = profile_dataset(rows, columns)
    except (DatasetError, OSError) as error: raise HTTPException(status_code=422, detail=str(error)) from error
    item.transformations = [*item.transformations, definition]; item.column_info = column_info; item.profile = profile
    db.commit(); return dataset_read(item, user)


@router.get("/datasets/{dataset_id}/download")
def download_dataset(dataset_id: str, db: DB, user: CurrentUser):
    item = db.get(PracticeDataset, dataset_id)
    if item is None or item.status == "ARCHIVED": raise HTTPException(status_code=404, detail="Dataset not found")
    permitted = item.owner_user_id == user.id or user.role == "admin" or (
        item.status == "PUBLISHED" and item.download_allowed and can_access(db, item, "dataset", user)
    )
    if not permitted: raise HTTPException(status_code=404, detail="Dataset not found")
    path = Path(item.storage_path)
    if not path.is_file(): raise HTTPException(status_code=410, detail="Dataset object is unavailable")
    if item.transformations:
        try:
            rows, _ = parse_dataset(path.read_bytes(), item.format)
            for transform in item.transformations: rows = transform_rows(rows, **transform)
        except DatasetError as error: raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(rows_to_csv(rows), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="cleaned-{item.id}.csv"'})
    return FileResponse(path, media_type=item.content_type, filename=item.original_filename)


@router.post("/datasets/{dataset_id}/practice", response_model=DatasetPracticeRead, status_code=status.HTTP_202_ACCEPTED)
def create_dataset_practice(dataset_id: str, payload: DatasetPracticeWrite, db: DB, user: CurrentUser,
                            enqueue: DatasetPracticeEnqueuer) -> DatasetPracticeRun:
    item = db.get(PracticeDataset, dataset_id)
    if item is None or item.status == "ARCHIVED" or not (
        item.owner_user_id == user.id or user.role == "admin" or (
            item.status == "PUBLISHED" and can_access(db, item, "dataset", user)
        )
    ):
        raise HTTPException(status_code=404, detail="Dataset not found")
    active = db.scalar(select(func.count(DatasetPracticeRun.id)).where(DatasetPracticeRun.user_id == user.id,
                                                                        DatasetPracticeRun.status.in_(["QUEUED", "RUNNING"]))) or 0
    if active >= 3: raise HTTPException(status_code=429, detail="Wait for an existing Data Lab run to finish")
    run = DatasetPracticeRun(id=str(uuid4()), user_id=user.id, dataset_id=item.id, technology=payload.technology,
                             source_code=payload.source_code, status="QUEUED")
    db.add(run); db.commit(); db.refresh(run)
    try: enqueue(run.id)
    except Exception:
        run.status, run.output, run.finished_at = "SYSTEM_ERROR", "The judge queue is unavailable. Please try again.", datetime.now(timezone.utc)
        db.commit(); db.refresh(run)
    return run


@router.get("/datasets/practice/{run_id}", response_model=DatasetPracticeRead)
def dataset_practice_result(run_id: str, db: DB, user: CurrentUser) -> DatasetPracticeRun:
    run = db.get(DatasetPracticeRun, run_id)
    if run is None or (run.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Data Lab run not found")
    return run


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, db: DB, user: CurrentUser) -> Response:
    item = own_dataset(db, dataset_id, user, allow_admin=False); path = Path(item.storage_path)
    item.status = "ARCHIVED"; db.commit()
    try: path.unlink(missing_ok=True)
    except OSError: pass
    return Response(status_code=204)


@router.patch("/admin/datasets/{dataset_id}", response_model=DatasetRead)
def manage_dataset(dataset_id: str, payload: dict[str, Any], request: Request, db: DB, admin: Admin) -> dict:
    item = own_dataset(db, dataset_id, admin)
    requested = payload.get("status")
    if requested not in {"PRIVATE", "PUBLISHED", "ARCHIVED"}: raise HTTPException(status_code=422, detail="Invalid dataset status")
    if requested == "PUBLISHED": require_publishable(db, item, "dataset")
    item.status = requested; item.owner_user_id = None if requested == "PUBLISHED" else item.owner_user_id
    audit(db, request, admin, "dataset.practice_status", "practice_dataset", item.id, {"status": requested})
    db.commit(); return dataset_read(item, admin)


@router.get("/admin/datasets", response_model=list[DatasetRead])
def admin_practice_datasets(db: DB, admin: Admin) -> list[dict]:
    items = db.scalars(select(PracticeDataset).order_by(PracticeDataset.created_at.desc()).limit(100)).all()
    return [dataset_read(item, admin) for item in items]


@router.post("/excel/evaluate", response_model=EvaluationRead)
def excel_evaluate(payload: ExpressionSubmission, user: CurrentUser) -> dict:
    del user
    try:
        result = evaluate_excel(payload.expression, payload.cells)
        passed = equivalent(result, payload.expected) if payload.expected is not None else None
        return {"valid": True, "passed": passed, "result": result,
                "feedback": "Formula is valid and matched the expected result." if passed else "Formula is valid." if passed is None else "Formula is valid but the result did not match.",
                "supported_subset": sorted(EXCEL_FUNCTIONS)}
    except ExpressionError as error:
        return {"valid": False, "passed": False, "result": None, "feedback": str(error), "supported_subset": sorted(EXCEL_FUNCTIONS)}


@router.post("/excel/evaluate-workbook", response_model=EvaluationRead)
def excel_workbook_evaluate(payload: WorkbookSubmission, user: CurrentUser) -> dict:
    del user
    try: content = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError):
        return {"valid": False, "passed": False, "result": None, "feedback": "Workbook content is not valid base64.", "supported_subset": sorted(EXCEL_FUNCTIONS)}
    if len(content) > settings().dataset_max_bytes:
        raise HTTPException(status_code=413, detail="Workbook exceeds the configured upload limit")
    try:
        validate_xlsx_archive(content)
        from openpyxl import load_workbook
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
        if len(workbook.sheetnames) > 20: raise ExpressionError("Workbook exceeds the 20-sheet limit")
        sheet = workbook.active
        formula = sheet[payload.answer_cell].value
        workbook.close()
        if not isinstance(formula, str) or not formula.startswith("="):
            raise ExpressionError(f"{payload.answer_cell} must contain a formula")
        fixture = {"A2": "West", "A3": "East", "A4": "West", "B2": 5, "B3": 8, "B4": 7, "E2": "West"}
        result = evaluate_excel(formula, fixture); passed = equivalent(result, 12)
        return {"valid": True, "passed": passed, "result": result,
                "feedback": "Workbook formula passed the hidden fixture." if passed else "Workbook formula did not produce the expected result.",
                "supported_subset": sorted(EXCEL_FUNCTIONS)}
    except ImportError:
        raise HTTPException(status_code=503, detail="XLSX evaluation support is unavailable")
    except (DatasetError, ExpressionError, OSError, ValueError, KeyError) as error:
        return {"valid": False, "passed": False, "result": None, "feedback": str(error), "supported_subset": sorted(EXCEL_FUNCTIONS)}


@router.post("/tableau/evaluate", response_model=EvaluationRead)
def tableau_evaluate(payload: ExpressionSubmission, user: CurrentUser) -> dict:
    del user
    try:
        if payload.rows:
            result = evaluate_tableau(payload.expression, payload.rows, payload.fields or None, payload.partition_by, payload.order_by)
        else:
            result = validate_tableau(payload.expression, payload.fields)
        passed = equivalent(result, payload.expected) if payload.expected is not None else None
        return {"valid": True, "passed": passed, "result": result,
                "feedback": "Expression is supported and evaluated successfully.", "supported_subset": sorted(TABLEAU_FUNCTIONS)}
    except ExpressionError as error:
        return {"valid": False, "passed": False, "result": None, "feedback": str(error), "supported_subset": sorted(TABLEAU_FUNCTIONS)}


@router.get("/multi-tool/challenges")
def multi_tool_challenges(db: DB, user: CurrentUser) -> list[dict[str, Any]]:
    progress = {(item.challenge_key, item.technology): item for item in db.scalars(select(MultiToolProgress).where(MultiToolProgress.user_id == user.id))}
    return [{**challenge, "progress": {technology: bool(progress.get((challenge["key"], technology)) and progress[(challenge["key"], technology)].completed)
                                           for technology in challenge["technologies"]}} for challenge in MULTI_TOOL_CHALLENGES]


@router.post("/multi-tool/submit", response_model=EvaluationRead)
def multi_tool_submit(payload: MultiToolSubmission, db: DB, user: CurrentUser) -> dict:
    challenge = next((item for item in MULTI_TOOL_CHALLENGES if item["key"] == payload.challenge_key), None)
    if challenge is None: raise HTTPException(status_code=404, detail="Multi-tool challenge not found")
    passed, feedback = grade_multi_tool(payload.technology, payload.answer)
    progress = db.scalar(select(MultiToolProgress).where(MultiToolProgress.user_id == user.id,
                                                         MultiToolProgress.challenge_key == payload.challenge_key,
                                                         MultiToolProgress.technology == payload.technology))
    if progress is None:
        progress = MultiToolProgress(user_id=user.id, challenge_key=payload.challenge_key, technology=payload.technology,
                                     completed=False, score=0); db.add(progress)
    progress.completed = bool(progress.completed) or passed; progress.score = max(progress.score or 0, 100 if passed else 0); db.commit()
    return {"valid": True, "passed": passed, "result": {"technology": payload.technology}, "feedback": feedback, "supported_subset": []}


def grade_multi_tool(technology: str, answer: str) -> tuple[bool, str]:
    normalized = re_normalize(answer)
    if technology == "SQL": passed = "selectregion,sum(sales)" in normalized and "fromorders" in normalized and "groupbyregion" in normalized
    elif technology == "PANDAS": passed = "groupby(" in normalized and "region" in normalized and "sales" in normalized and ".sum(" in normalized
    elif technology == "PYSPARK": passed = "groupby(" in normalized and "region" in normalized and "sum(" in normalized and "sales" in normalized
    elif technology == "EXCEL":
        try: passed = equivalent(evaluate_excel(answer, {"A2": "West", "A3": "East", "A4": "West", "B2": 5, "B3": 8, "B4": 7, "E2": "West"}), 12)
        except ExpressionError: passed = False
    else:
        try: passed = evaluate_tableau(answer, [{"Region": "West", "Sales": 5}, {"Region": "East", "Sales": 8}, {"Region": "West", "Sales": 7}]) == {"West": 12.0, "East": 8.0}
        except ExpressionError: passed = False
    return passed, "Solution passed the technology-specific hidden checks." if passed else "Review grouping, field names, and aggregation semantics."


def re_normalize(value: str) -> str:
    return "".join(value.lower().replace("`", "").replace('"', "").split())


@router.get("/analytics", response_model=AnalyticsRead)
def skill_analytics(db: DB, user: CurrentUser) -> dict:
    subject_rows = db.execute(select(Problem.category, func.count(Submission.id),
                                     func.sum(case((Submission.verdict == "ACCEPTED", 1), else_=0)))
                              .join(Problem, Problem.slug == Submission.problem_slug)
                              .where(Submission.user_id == user.id, Submission.mode == "SUBMIT")
                              .group_by(Problem.category)).all()
    subjects = [{"subject": category, "attempted": attempted, "solved": solved or 0,
                 "accuracy": round((solved or 0) / attempted * 100, 2) if attempted else 0} for category, attempted, solved in subject_rows]
    assessment_count = db.scalar(select(func.count(AssessmentAttempt.id)).where(AssessmentAttempt.user_id == user.id,
                                                                                 AssessmentAttempt.status != "IN_PROGRESS")) or 0
    daily_rows = db.execute(select(func.date(Submission.created_at), func.count(Submission.id),
                                   func.sum(case((Submission.verdict == "ACCEPTED", 1), else_=0)))
                            .where(Submission.user_id == user.id).group_by(func.date(Submission.created_at))
                            .order_by(func.date(Submission.created_at).desc()).limit(30)).all()
    attempts = sum(item["attempted"] for item in subjects); solved = sum(item["solved"] for item in subjects)
    return {"totals": {"questions_attempted": attempts, "questions_solved": solved,
                       "accuracy": round(solved / attempts * 100, 2) if attempts else 0,
                       "assessments_completed": assessment_count}, "subjects": subjects,
            "daily": [{"day": str(day), "attempted": attempted, "solved": accepted or 0} for day, attempted, accepted in reversed(daily_rows)],
            "weak_topics": [item["subject"] for item in subjects if item["attempted"] >= 2 and item["accuracy"] < 50][:5]}
