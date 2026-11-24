import base64
import binascii
import csv
import hashlib
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .access_control import access_summary, prevent_unconfirmed_inline_change, replace_students, require_publishable, target, validate_students
from .auth import require_admin
from .cache import invalidate_public
from .config import settings
from .main_dependencies import get_db
from .judge_client import Enqueuer
from .models import (
    Achievement, AuditLog, Contest, ContestProblem, ContestRating, ContestRegistration,
    ContestSubmission, LearningPath, LearningPathProblem, LearningPathProgress, ManagedDataset,
    Problem, ProblemEvaluator, Profile, RankHistory, StarterCode, Submission, TestCase, User,
    UserAchievement, XPTransaction,
)
from .schemas_admin import (
    AdminAchievementRead, AdminAchievementWrite, AdminContestRead, AdminContestWrite,
    AdminContestRegistrationRead, AdminContestStandingRead, AdminContestSubmissionRead,
    AdminDatasetRead, AdminOverview, AdminPathRead, AdminPathWrite, AdminProblemDetail,
    AdminProblemRead, AdminProblemWrite, AdminRankHistoryRead, AdminUserRead,
    AdminXPTransactionRead, AuditLogRead, ContestStatusUpdate, DatasetStatusUpdate, DatasetUpload,
    JudgeRecoveryRead, ProblemStatusUpdate, StudentAccessWrite, UserStatusUpdate,
)
from .problem_uniqueness import find_duplicates
from .contest_routes import calculate_standings

router = APIRouter(prefix="/admin", tags=["administration"])
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


def record_audit(
    db: Session, request: Request, actor: User, action: str, target_type: str,
    target_id: str, details: dict | None = None,
) -> None:
    db.add(AuditLog(
        actor_user_id=actor.id, action=action, target_type=target_type, target_id=target_id,
        details=details or {}, ip_address=request.client.host if request.client else None,
    ))


def page_limit(limit: int) -> int:
    return min(max(limit, 1), 100)




@router.get("/students")
def available_students(
    db: DB, admin: Admin, q: Annotated[str, Query(max_length=100)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict]:
    """Search only active learner accounts; never expose passwords or tokens."""
    filters = [User.role == "learner", User.is_active.is_(True)]
    if q.strip():
        term = q.strip().lower()
        filters.append(or_(func.lower(User.username).contains(term, autoescape=True),
                           func.lower(User.email).contains(term, autoescape=True)))
    users = db.scalars(select(User).where(*filters).order_by(User.username).limit(limit)).all()
    return [{"id": user.id, "username": user.username, "display_name": user.profile.display_name}
            for user in users]


@router.get("/access/{kind}/{identifier}")
def read_content_access(kind: str, identifier: str, db: DB, admin: Admin) -> dict:
    item = target(db, kind, identifier)
    if item is None: raise HTTPException(status_code=404, detail="Content not found")
    return access_summary(db, item, kind)


@router.post("/access/{kind}/{identifier}/preview")
def preview_content_access(kind: str, identifier: str, payload: StudentAccessWrite, db: DB, admin: Admin) -> dict:
    item = target(db, kind, identifier)
    if item is None: raise HTTPException(status_code=404, detail="Content not found")
    if payload.assigned_user_ids is not None: validate_students(db, payload.assigned_user_ids)
    current = access_summary(db, item, kind)
    next_ids = payload.assigned_user_ids if payload.assigned_user_ids is not None else current["assigned_user_ids"]
    return {
        "current_scope": item.access_scope,
        "next_scope": payload.access_scope,
        "currently_assigned": len(current["assigned_user_ids"]),
        "next_assigned": len(next_ids),
        "scope_change": item.access_scope != payload.access_scope,
        "may_remove_access": current["published"] and (
            (item.access_scope == "ALL" and payload.access_scope == "SELECTED")
            or (item.access_scope == "SELECTED" and payload.access_scope == "SELECTED"
                and bool(set(current["assigned_user_ids"]) - set(next_ids)))
        ),
        "preserves_submissions": True,
    }


@router.patch("/access/{kind}/{identifier}")
def update_content_access(
    kind: str, identifier: str, payload: StudentAccessWrite,
    request: Request, db: DB, admin: Admin,
) -> dict:
    item = target(db, kind, identifier)
    if item is None: raise HTTPException(status_code=404, detail="Content not found")
    if kind == "contest" and item.publication_status == "FINALIZED":
        raise HTTPException(status_code=409, detail="Finalized contest access cannot be changed")
    before = access_summary(db, item, kind)
    changed = item.access_scope != payload.access_scope or (
        payload.assigned_user_ids is not None
        and sorted(payload.assigned_user_ids) != before["assigned_user_ids"]
    )
    if before["published"] and changed and not payload.confirm_impact:
        raise HTTPException(status_code=409, detail="Confirm the impact of changing published student access")
    if payload.assigned_user_ids is not None:
        replace_students(db, kind, identifier, payload.assigned_user_ids)
    item.access_scope = payload.access_scope
    if before["published"]: require_publishable(db, item, kind)
    record_audit(db, request, admin, "content.access", kind, identifier, {
        "previous": before, "next_scope": item.access_scope,
        "next_assigned": access_summary(db, item, kind)["assigned_user_ids"], "reason": payload.reason,
    })
    db.commit()
    invalidate_public("catalog", "problem", "learning", "contest")
    return access_summary(db, item, kind)

@router.get("/overview", response_model=AdminOverview)
def overview(db: DB, admin: Admin) -> dict:
    del admin
    now = datetime.now(timezone.utc)
    failed = {"WRONG_ANSWER", "COMPILATION_ERROR", "RUNTIME_ERROR", "TIME_LIMIT_EXCEEDED", "MEMORY_LIMIT_EXCEEDED"}
    registrations = db.execute(
        select(func.date(User.created_at), func.count()).group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at).desc()).limit(14)
    ).all()
    submissions = db.execute(
        select(func.date(Submission.created_at), func.count()).group_by(func.date(Submission.created_at))
        .order_by(func.date(Submission.created_at).desc()).limit(14)
    ).all()
    recent = db.execute(
        select(User, Profile).join(Profile, Profile.user_id == User.id)
        .order_by(User.created_at.desc()).limit(8)
    ).all()
    recent_submissions = list(db.scalars(
        select(Submission).where(Submission.started_at.is_not(None)).order_by(Submission.created_at.desc()).limit(500)
    ))
    queue_ms = [
        (item.started_at - item.created_at).total_seconds() * 1000
        for item in recent_submissions if item.started_at is not None
    ]
    execution_ms = [item.execution_ms for item in recent_submissions if item.execution_ms is not None]
    stuck_before = now - timedelta(seconds=settings().judge_stuck_seconds)
    return {
        "total_users": db.scalar(select(func.count(User.id))) or 0,
        "active_users": db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0,
        "total_problems": db.scalar(select(func.count(Problem.slug))) or 0,
        "published_problems": db.scalar(select(func.count(Problem.slug)).where(Problem.status == "PUBLISHED")) or 0,
        "total_submissions": db.scalar(select(func.count(Submission.id))) or 0,
        "accepted_submissions": db.scalar(select(func.count(Submission.id)).where(Submission.verdict == "ACCEPTED")) or 0,
        "failed_submissions": db.scalar(select(func.count(Submission.id)).where(Submission.verdict.in_(failed))) or 0,
        "active_contests": db.scalar(select(func.count(Contest.id)).where(
            Contest.publication_status == "PUBLISHED", Contest.starts_at <= now, Contest.ends_at > now,
        )) or 0,
        "queued_submissions": db.scalar(select(func.count(Submission.id)).where(Submission.status == "QUEUED")) or 0,
        "running_submissions": db.scalar(select(func.count(Submission.id)).where(Submission.status == "RUNNING")) or 0,
        "stuck_submissions": db.scalar(select(func.count(Submission.id)).where(
            Submission.status == "RUNNING", Submission.started_at < stuck_before,
        )) or 0,
        "cancelled_submissions": db.scalar(select(func.count(Submission.id)).where(Submission.status == "CANCELLED")) or 0,
        "average_queue_ms": round(sum(queue_ms) / len(queue_ms), 2) if queue_ms else None,
        "average_execution_ms": round(sum(execution_ms) / len(execution_ms), 2) if execution_ms else None,
        "registration_trend": [{"day": str(day), "count": count} for day, count in reversed(registrations)],
        "submission_trend": [{"day": str(day), "count": count} for day, count in reversed(submissions)],
        "recent_registrations": [
            {"username": user.username, "display_name": profile.display_name, "created_at": user.created_at}
            for user, profile in recent
        ],
    }


@router.post("/judge/recover-stuck", response_model=JudgeRecoveryRead)
def recover_stuck_submissions(
    request: Request, db: DB, admin: Admin, enqueue: Enqueuer,
) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings().judge_stuck_seconds)
    items = list(db.scalars(
        select(Submission).where(
            Submission.status == "RUNNING", Submission.started_at < cutoff,
        ).order_by(Submission.started_at).limit(100).with_for_update(skip_locked=True)
    ))
    requeue: list[str] = []
    cancelled = 0
    for item in items:
        if item.cancel_requested_at is not None:
            item.status = "CANCELLED"
            item.verdict = "CANCELLED"
            item.output = "Submission cancelled during stuck-task recovery."
            item.finished_at = datetime.now(timezone.utc)
            cancelled += 1
        else:
            item.status = "QUEUED"
            item.started_at = None
            requeue.append(item.id)
    if items:
        record_audit(db, request, admin, "judge.recover_stuck", "submission_batch", "stuck", {
            "requeued": len(requeue), "cancelled": cancelled,
        })
    db.commit()
    failed = 0
    for submission_id in requeue:
        try:
            enqueue(submission_id)
        except Exception:
            failed += 1
            item = db.get(Submission, submission_id)
            if item is not None and item.status == "QUEUED":
                item.status = "SYSTEM_ERROR"
                item.verdict = "SYSTEM_ERROR"
                item.output = "The judge queue was unavailable during recovery."
                item.finished_at = datetime.now(timezone.utc)
                db.commit()
    return {"recovered": len(requeue), "cancelled": cancelled, "failed_to_enqueue": failed}


def problem_summary(problem: Problem, db: Session | None = None) -> dict:
    return {
        "slug": problem.slug, "title": problem.title, "category": problem.category,
        "difficulty": problem.difficulty, "format": problem.format, "topic": problem.topic,
        "status": problem.status, "access_scope": problem.access_scope,
        "assigned_count": len(access_summary(db, problem, "problem")["assigned_user_ids"]) if db is not None else 0,
        "supported_languages": [starter.language for starter in problem.starters],
        "test_case_count": len(problem.test_cases),
        "hidden_test_count": sum(case.is_hidden for case in problem.test_cases),
    }


@router.get("/problems", response_model=list[AdminProblemRead])
def admin_problems(
    db: DB, admin: Admin, q: Annotated[str, Query(max_length=100)] = "",
    problem_status: Annotated[str | None, Query(alias="status", max_length=16)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    del admin
    filters = []
    if q.strip():
        term = q.strip().lower()
        filters.append(or_(func.lower(Problem.title).contains(term), func.lower(Problem.slug).contains(term)))
    if problem_status:
        filters.append(Problem.status == problem_status)
    problems = db.scalars(select(Problem).where(*filters).order_by(Problem.title).limit(limit).offset(offset)).all()
    return [problem_summary(problem, db) for problem in problems]


@router.get("/problems/duplicate-check")
def check_problem_duplicate(
    db: DB, admin: Admin,
    title: Annotated[str, Query(min_length=1, max_length=160)],
    category: Annotated[str, Query(min_length=1, max_length=24)],
    format: Annotated[str, Query(min_length=1, max_length=24)],
    topic: Annotated[str, Query(max_length=80)] = "",
    description: Annotated[str, Query(max_length=1000)] = "",
    exclude_slug: Annotated[str, Query(max_length=100)] = "",
) -> dict:
    """Conservative matches only. A shared learning path must reference existing slugs."""
    del admin
    categories = ["foundations", "code"] if category in {"foundations", "code"} else [category]
    candidates = db.scalars(select(Problem).where(Problem.category.in_(categories))).all()
    proposal = {
        "slug": exclude_slug, "title": title, "category": category,
        "format": format, "topic": topic, "description": description,
    }
    return {"duplicates": find_duplicates(proposal, candidates)}


@router.get("/problems/{slug}", response_model=AdminProblemDetail)
def admin_problem(slug: str, db: DB, admin: Admin) -> dict:
    del admin
    problem = db.get(Problem, slug)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    evaluator = db.get(ProblemEvaluator, slug)
    return problem_summary(problem, db) | {
        "tags": problem.tags, "description": problem.description, "constraints": problem.constraints,
        "examples": problem.examples, "choices": problem.choices,
        "starters": [{"language": item.language, "code": item.code} for item in problem.starters],
        "test_cases": [{
            "input_data": item.input_data, "expected_output": item.expected_output,
            "is_hidden": item.is_hidden, "position": item.position, "tolerance": item.tolerance,
        } for item in sorted(problem.test_cases, key=lambda case: (case.position, case.id))],
        "evaluator": None if evaluator is None else {"kind": evaluator.kind, "config": evaluator.config},
    }


@router.put("/problems/{slug}", response_model=AdminProblemDetail)
def save_problem(slug: str, payload: AdminProblemWrite, request: Request, db: DB, admin: Admin) -> dict:
    if not slug or len(slug) > 100 or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in slug):
        raise HTTPException(status_code=422, detail="Problem slug is invalid")
    problem = db.get(Problem, slug)
    if problem is not None:
        prevent_unconfirmed_inline_change(db, problem, "problem", payload.model_fields_set, payload.access_scope, payload.assigned_user_ids)
    if problem is None or any(
        field in payload.model_fields_set
        for field in ("title", "description", "category", "topic", "format")
    ):
        categories = ["foundations", "code"] if payload.category in {"foundations", "code"} else [payload.category]
        candidates = db.scalars(select(Problem).where(Problem.category.in_(categories))).all()
        proposal = payload.model_dump() | {"slug": slug}
        duplicates = find_duplicates(proposal, candidates)
        # Edits to the existing grandfathered legacy pair are permitted only
        # when the question's identity is unchanged.
        if problem is not None and {
            "title": payload.title, "description": payload.description,
            "category": payload.category, "topic": payload.topic, "format": payload.format,
        } == {
            "title": problem.title, "description": problem.description,
            "category": problem.category, "topic": problem.topic, "format": problem.format,
        }:
            duplicates = []
        if duplicates:
            conflict = duplicates[0]
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "This question already exists. Edit or reuse the existing problem instead of creating a duplicate.",
                    "existing_slug": conflict["slug"],
                    "existing_title": conflict["title"],
                    "reason": conflict["reason"],
                },
            )
    action = "problem.update" if problem else "problem.create"
    values = payload.model_dump(exclude={"starters", "test_cases", "evaluator", "assigned_user_ids"})
    if problem is not None and "access_scope" not in payload.model_fields_set:
        values.pop("access_scope", None)
    if problem is None:
        problem = Problem(slug=slug, starters=[], test_cases=[], **values)
        db.add(problem)
    else:
        for key, value in values.items():
            setattr(problem, key, value)
        problem.starters.clear()
        problem.test_cases.clear()
    if "assigned_user_ids" in payload.model_fields_set:
        replace_students(db, "problem", slug, payload.assigned_user_ids)
    if problem.status == "PUBLISHED": require_publishable(db, problem, "problem")
    problem.starters.extend(StarterCode(**starter.model_dump()) for starter in payload.starters)
    problem.test_cases.extend(TestCase(**case.model_dump()) for case in payload.test_cases)
    if payload.evaluator is None:
        evaluator = db.get(ProblemEvaluator, slug)
        if evaluator is not None:
            db.delete(evaluator)
    else:
        db.merge(ProblemEvaluator(problem_slug=slug, **payload.evaluator.model_dump()))
    record_audit(db, request, admin, action, "problem", slug, {"status": payload.status})
    db.commit()
    invalidate_public("catalog", "problem")
    return admin_problem(slug, db, admin)


@router.patch("/problems/{slug}/status", response_model=AdminProblemRead)
def set_problem_status(
    slug: str, payload: ProblemStatusUpdate, request: Request, db: DB, admin: Admin,
) -> dict:
    problem = db.get(Problem, slug)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    if payload.status == "PUBLISHED": require_publishable(db, problem, "problem")
    if payload.status == "PUBLISHED" and not problem.test_cases:
        raise HTTPException(status_code=409, detail="A published problem requires test cases")
    previous = problem.status
    problem.status = payload.status
    record_audit(db, request, admin, "problem.status", "problem", slug, {
        "from": previous, "to": payload.status, "reason": payload.reason,
    })
    db.commit()
    invalidate_public("catalog", "problem")
    return problem_summary(problem, db)


def validate_dataset(filename: str, content_type: str, content: bytes) -> str:
    if Path(filename).name != filename:
        raise HTTPException(status_code=422, detail="Dataset filename must not contain a path")
    suffix = Path(filename).suffix.lower()
    allowed = {
        ".csv": {"text/csv", "application/csv", "text/plain"},
        ".json": {"application/json", "text/json"},
        ".parquet": {"application/octet-stream", "application/vnd.apache.parquet"},
    }
    if suffix not in allowed or content_type not in allowed[suffix]:
        raise HTTPException(status_code=422, detail="Dataset file type is not allowed")
    try:
        if suffix == ".json":
            json.loads(content)
        elif suffix == ".csv":
            rows = list(csv.reader(io.StringIO(content.decode("utf-8"))))
            if not rows or not rows[0] or len(rows) > 1_000_000:
                raise ValueError
        elif not (content.startswith(b"PAR1") and content.endswith(b"PAR1")):
            raise ValueError
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Dataset content is invalid") from error
    return suffix


@router.get("/datasets", response_model=list[AdminDatasetRead])
def datasets(
    db: DB, admin: Admin, limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ManagedDataset]:
    del admin
    return list(db.scalars(select(ManagedDataset).order_by(
        ManagedDataset.created_at.desc(), ManagedDataset.id,
    ).limit(limit).offset(offset)))


@router.post("/datasets", response_model=AdminDatasetRead, status_code=status.HTTP_201_CREATED)
def upload_dataset(payload: DatasetUpload, request: Request, db: DB, admin: Admin) -> ManagedDataset:
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(status_code=422, detail="Dataset content is not valid base64") from error
    configuration = settings()
    if not content or len(content) > configuration.dataset_max_bytes:
        raise HTTPException(status_code=413, detail="Dataset exceeds the configured size limit")
    suffix = validate_dataset(payload.filename, payload.content_type, content)
    version = (db.scalar(select(func.max(ManagedDataset.version)).where(ManagedDataset.name == payload.name)) or 0) + 1
    dataset_id = str(uuid4())
    digest = hashlib.sha256(content).hexdigest()
    configuration.dataset_storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    storage = configuration.dataset_storage_dir / f"{dataset_id}{suffix}"
    temporary = configuration.dataset_storage_dir / f".{dataset_id}.tmp"
    temporary.write_bytes(content)
    temporary.chmod(0o600)
    temporary.replace(storage)
    item = ManagedDataset(
        id=dataset_id, name=payload.name, kind=payload.kind, version=version,
        original_filename=payload.filename, content_type=payload.content_type,
        size_bytes=len(content), sha256=digest, storage_path=str(storage), created_by=admin.id,
    )
    db.add(item)
    record_audit(db, request, admin, "dataset.upload", "dataset", dataset_id, {
        "name": payload.name, "kind": payload.kind, "version": version, "size_bytes": len(content),
    })
    try:
        db.commit()
    except Exception:
        storage.unlink(missing_ok=True)
        raise
    db.refresh(item)
    return item


@router.get("/datasets/{dataset_id}/download", response_class=FileResponse)
def download_dataset(dataset_id: str, db: DB, admin: Admin) -> FileResponse:
    del admin
    item = db.get(ManagedDataset, dataset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    path = Path(item.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=410, detail="Dataset file is unavailable")
    return FileResponse(path, media_type=item.content_type, filename=item.original_filename)


@router.patch("/datasets/{dataset_id}", response_model=AdminDatasetRead)
def set_dataset_status(
    dataset_id: str, payload: DatasetStatusUpdate, request: Request, db: DB, admin: Admin,
) -> ManagedDataset:
    item = db.get(ManagedDataset, dataset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    item.is_active = payload.is_active
    record_audit(db, request, admin, "dataset.status", "dataset", dataset_id, {
        "is_active": payload.is_active, "reason": payload.reason,
    })
    db.commit()
    db.refresh(item)
    return item


def user_rows(db: Session, filters: list, limit: int, offset: int) -> list[dict]:
    submission_count = select(func.count(Submission.id)).where(Submission.user_id == User.id).correlate(User).scalar_subquery()
    accepted_count = select(func.count(Submission.id)).where(
        Submission.user_id == User.id, Submission.verdict == "ACCEPTED",
    ).correlate(User).scalar_subquery()
    error_count = select(func.count(Submission.id)).where(
        Submission.user_id == User.id, Submission.verdict == "SYSTEM_ERROR",
    ).correlate(User).scalar_subquery()
    rows = db.execute(select(
        User, Profile.display_name, submission_count, accepted_count, error_count,
    ).join(Profile, Profile.user_id == User.id).where(*filters).order_by(User.created_at.desc()).limit(limit).offset(offset)).all()
    return [{
        "id": user.id, "email": user.email, "username": user.username, "display_name": display_name,
        "role": user.role, "is_active": user.is_active, "email_verified": user.email_verified,
        "created_at": user.created_at, "last_login_at": user.last_login_at,
        "submissions": submissions, "accepted_submissions": accepted, "system_errors": errors,
    } for user, display_name, submissions, accepted, errors in rows]


@router.get("/users", response_model=list[AdminUserRead])
def users(
    db: DB, admin: Admin, q: Annotated[str, Query(max_length=100)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    del admin
    filters = []
    if q.strip():
        term = q.strip().lower()
        filters.append(or_(
            func.lower(User.username).contains(term), func.lower(User.email).contains(term),
            func.lower(Profile.display_name).contains(term),
        ))
    return user_rows(db, filters, limit, offset)


@router.get("/users/{user_id}", response_model=AdminUserRead)
def user_detail(user_id: int, db: DB, admin: Admin) -> dict:
    del admin
    rows = user_rows(db, [User.id == user_id], 1, 0)
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    return rows[0]


@router.patch("/users/{user_id}/status", response_model=AdminUserRead)
def set_user_status(
    user_id: int, payload: UserStatusUpdate, request: Request, db: DB, admin: Admin,
) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=409, detail="Administrators cannot suspend their own active session")
    previous = user.is_active
    user.is_active = payload.is_active
    record_audit(db, request, admin, "user.status", "user", str(user_id), {
        "from": previous, "to": payload.is_active, "reason": payload.reason,
    })
    db.commit()
    return user_detail(user_id, db, admin)


def contest_summary(db: Session, contest: Contest, counts: tuple[int, int, int] | None = None) -> dict:
    if counts is None:
        counts = (
            db.scalar(select(func.count(ContestRegistration.id)).where(ContestRegistration.contest_id == contest.id)) or 0,
            db.scalar(select(func.count(ContestSubmission.id)).where(ContestSubmission.contest_id == contest.id)) or 0,
            db.scalar(select(func.count(ContestProblem.problem_slug)).where(ContestProblem.contest_id == contest.id)) or 0,
        )
    return {
        "slug": contest.slug, "title": contest.title, "starts_at": contest.starts_at,
        "ends_at": contest.ends_at, "is_rated": contest.is_rated,
        "publication_status": contest.publication_status,
        "access_scope": contest.access_scope,
        "assigned_count": access_summary(db, contest, "contest")["assigned_count"],
        "registrations": counts[0], "submissions": counts[1], "problem_count": counts[2],
    }


@router.get("/contests", response_model=list[AdminContestRead])
def admin_contests(db: DB, admin: Admin) -> list[dict]:
    del admin
    registrations = select(func.count(ContestRegistration.id)).where(
        ContestRegistration.contest_id == Contest.id,
    ).correlate(Contest).scalar_subquery()
    submissions = select(func.count(ContestSubmission.id)).where(
        ContestSubmission.contest_id == Contest.id,
    ).correlate(Contest).scalar_subquery()
    problems = select(func.count(ContestProblem.problem_slug)).where(
        ContestProblem.contest_id == Contest.id,
    ).correlate(Contest).scalar_subquery()
    rows = db.execute(select(Contest, registrations, submissions, problems).order_by(
        Contest.starts_at.desc(), Contest.id,
    ).limit(100)).all()
    return [contest_summary(db, contest, (registration_count, submission_count, problem_count))
            for contest, registration_count, submission_count, problem_count in rows]


def managed_contest(db: Session, slug: str) -> Contest:
    contest = db.scalar(select(Contest).where(Contest.slug == slug))
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    return contest


@router.get(
    "/contests/{slug}/registrations",
    response_model=list[AdminContestRegistrationRead],
)
def contest_registrations(slug: str, db: DB, admin: Admin) -> list[dict]:
    del admin
    contest = managed_contest(db, slug)
    rows = db.execute(
        select(ContestRegistration, User, Profile)
        .join(User, User.id == ContestRegistration.user_id)
        .join(Profile, Profile.user_id == User.id)
        .where(ContestRegistration.contest_id == contest.id)
        .order_by(ContestRegistration.registered_at.desc())
        .limit(500)
    ).all()
    return [{
        "user_id": user.id, "username": user.username, "display_name": profile.display_name,
        "registered_at": registration.registered_at,
    } for registration, user, profile in rows]


@router.get("/contests/{slug}/standings", response_model=list[AdminContestStandingRead])
def contest_standings(slug: str, db: DB, admin: Admin) -> list[dict]:
    del admin
    return calculate_standings(db, managed_contest(db, slug))


@router.get(
    "/contests/{slug}/submissions",
    response_model=list[AdminContestSubmissionRead],
)
def contest_submissions(slug: str, db: DB, admin: Admin) -> list[dict]:
    del admin
    contest = managed_contest(db, slug)
    rows = db.execute(
        select(ContestSubmission, Submission, User.username)
        .join(Submission, Submission.id == ContestSubmission.submission_id)
        .join(User, User.id == ContestSubmission.user_id)
        .where(ContestSubmission.contest_id == contest.id)
        .order_by(ContestSubmission.submitted_at.desc())
        .limit(500)
    ).all()
    return [{
        "submission_id": item.submission_id, "username": username,
        "problem_slug": item.problem_slug, "language": submission.language,
        "status": submission.status, "verdict": submission.verdict,
        "submitted_at": item.submitted_at,
    } for item, submission, username in rows]


@router.put("/contests/{slug}", response_model=AdminContestRead)
def save_contest(slug: str, payload: AdminContestWrite, request: Request, db: DB, admin: Admin) -> dict:
    if payload.publication_status == "FINALIZED":
        raise HTTPException(
            status_code=422,
            detail="Contest finalization is only available through the verified results workflow",
        )
    contest = db.scalar(select(Contest).where(Contest.slug == slug).with_for_update())
    if contest is not None and (
        contest.publication_status == "FINALIZED"
        or db.scalar(select(ContestRating.id).where(ContestRating.contest_id == contest.id)) is not None
    ):
        raise HTTPException(status_code=409, detail="Finalized contest results cannot be edited")
    for assignment in payload.problems:
        if db.get(Problem, assignment.problem_slug) is None:
            raise HTTPException(status_code=422, detail=f"Problem does not exist: {assignment.problem_slug}")
    if contest is not None:
        prevent_unconfirmed_inline_change(db, contest, "contest", payload.model_fields_set, payload.access_scope, payload.assigned_user_ids)
    action = "contest.update" if contest else "contest.create"
    values = payload.model_dump(exclude={"problems", "assigned_user_ids"})
    if contest is not None and "access_scope" not in payload.model_fields_set:
        values.pop("access_scope", None)
    if contest is None:
        contest = Contest(slug=slug, **values)
        db.add(contest)
        db.flush()
    else:
        for key, value in values.items():
            setattr(contest, key, value)
        for assignment in db.scalars(select(ContestProblem).where(ContestProblem.contest_id == contest.id)):
            db.delete(assignment)
        db.flush()
    if "assigned_user_ids" in payload.model_fields_set:
        replace_students(db, "contest", slug, payload.assigned_user_ids)
    if contest.publication_status == "PUBLISHED": require_publishable(db, contest, "contest")
    for position, assignment in enumerate(payload.problems, 1):
        db.add(ContestProblem(
            contest_id=contest.id, problem_slug=assignment.problem_slug,
            position=position, points=assignment.points,
        ))
    record_audit(db, request, admin, action, "contest", slug, {"status": payload.publication_status})
    db.commit()
    invalidate_public("contest")
    return contest_summary(db, contest)


@router.patch("/contests/{slug}/status", response_model=AdminContestRead)
def set_contest_status(
    slug: str, payload: ContestStatusUpdate, request: Request, db: DB, admin: Admin,
) -> dict:
    contest = db.scalar(select(Contest).where(Contest.slug == slug).with_for_update())
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    if payload.status == "FINALIZED":
        raise HTTPException(
            status_code=422,
            detail="Contest finalization is only available through the verified results workflow",
        )
    if contest.publication_status == "FINALIZED" or db.scalar(
        select(ContestRating.id).where(ContestRating.contest_id == contest.id)
    ) is not None:
        raise HTTPException(status_code=409, detail="Finalized contest results cannot be changed")
    if payload.status == "PUBLISHED": require_publishable(db, contest, "contest")
    previous = contest.publication_status
    contest.publication_status = payload.status
    record_audit(db, request, admin, "contest.status", "contest", slug, {
        "from": previous, "to": payload.status, "reason": payload.reason,
    })
    db.commit()
    invalidate_public("contest")
    return contest_summary(db, contest)


def path_summary(db: Session, path: LearningPath, counts: tuple[int, int] | None = None) -> dict:
    if counts is None:
        counts = (
            db.scalar(select(func.count(LearningPathProblem.problem_slug)).where(LearningPathProblem.path_slug == path.slug)) or 0,
            db.scalar(select(func.count(LearningPathProgress.id)).where(LearningPathProgress.path_slug == path.slug)) or 0,
        )
    return {
        "slug": path.slug, "title": path.title, "status": path.status,
        "access_scope": path.access_scope,
        "assigned_count": access_summary(db, path, "path")["assigned_count"],
        "prerequisites": path.prerequisites,
        "problem_count": counts[0], "enrollments": counts[1],
    }


@router.get("/paths", response_model=list[AdminPathRead])
def admin_paths(db: DB, admin: Admin) -> list[dict]:
    del admin
    problems = select(func.count(LearningPathProblem.problem_slug)).where(
        LearningPathProblem.path_slug == LearningPath.slug,
    ).correlate(LearningPath).scalar_subquery()
    enrollments = select(func.count(LearningPathProgress.id)).where(
        LearningPathProgress.path_slug == LearningPath.slug,
    ).correlate(LearningPath).scalar_subquery()
    rows = db.execute(select(LearningPath, problems, enrollments).order_by(LearningPath.title)).all()
    return [path_summary(db, path, (problem_count, enrollment_count))
            for path, problem_count, enrollment_count in rows]


@router.put("/paths/{slug}", response_model=AdminPathRead)
def save_path(slug: str, payload: AdminPathWrite, request: Request, db: DB, admin: Admin) -> dict:
    if slug in payload.prerequisites:
        raise HTTPException(status_code=422, detail="A path cannot require itself")
    for prerequisite in payload.prerequisites:
        if db.get(LearningPath, prerequisite) is None:
            raise HTTPException(status_code=422, detail=f"Prerequisite path does not exist: {prerequisite}")
    for assignment in payload.problems:
        if db.get(Problem, assignment.problem_slug) is None:
            raise HTTPException(status_code=422, detail=f"Problem does not exist: {assignment.problem_slug}")
    path = db.get(LearningPath, slug)
    if path is not None:
        prevent_unconfirmed_inline_change(db, path, "path", payload.model_fields_set, payload.access_scope, payload.assigned_user_ids)
    action = "path.update" if path else "path.create"
    values = payload.model_dump(exclude={"problems", "assigned_user_ids"})
    if path is not None and "access_scope" not in payload.model_fields_set:
        values.pop("access_scope", None)
    if path is None:
        path = LearningPath(slug=slug, **values)
        db.add(path)
    else:
        for key, value in values.items():
            setattr(path, key, value)
        for assignment in db.scalars(select(LearningPathProblem).where(LearningPathProblem.path_slug == slug)):
            db.delete(assignment)
        db.flush()
    if "assigned_user_ids" in payload.model_fields_set:
        replace_students(db, "path", slug, payload.assigned_user_ids)
    if path.status == "PUBLISHED": require_publishable(db, path, "path")
    for position, assignment in enumerate(payload.problems, 1):
        db.add(LearningPathProblem(
            path_slug=slug, problem_slug=assignment.problem_slug,
            position=position, milestone=assignment.milestone,
        ))
    record_audit(db, request, admin, action, "learning_path", slug, {"status": payload.status})
    db.commit()
    invalidate_public("learning")
    return path_summary(db, path)


def achievement_summary(db: Session, achievement: Achievement, awarded_count: int | None = None) -> dict:
    if awarded_count is None:
        awarded_count = db.scalar(select(func.count(UserAchievement.id)).where(
            UserAchievement.achievement_slug == achievement.slug,
        )) or 0
    return {
        "slug": achievement.slug, "name": achievement.name, "description": achievement.description,
        "criteria": achievement.criteria, "xp_reward": achievement.xp_reward,
        "awarded_count": awarded_count,
    }


@router.get("/achievements", response_model=list[AdminAchievementRead])
def admin_achievements(db: DB, admin: Admin) -> list[dict]:
    del admin
    awarded = select(func.count(UserAchievement.id)).where(
        UserAchievement.achievement_slug == Achievement.slug,
    ).correlate(Achievement).scalar_subquery()
    rows = db.execute(select(Achievement, awarded).order_by(Achievement.name)).all()
    return [achievement_summary(db, item, awarded_count) for item, awarded_count in rows]


@router.put("/achievements/{slug}", response_model=AdminAchievementRead)
def save_achievement(
    slug: str, payload: AdminAchievementWrite, request: Request, db: DB, admin: Admin,
) -> dict:
    allowed_criteria = {"solved", "difficulty", "category", "topic", "count", "streak"}
    if not payload.criteria or not set(payload.criteria).issubset(allowed_criteria):
        raise HTTPException(status_code=422, detail="Achievement criteria are unsupported")
    achievement = db.get(Achievement, slug)
    action = "achievement.update" if achievement else "achievement.create"
    if achievement is None:
        achievement = Achievement(slug=slug, **payload.model_dump())
        db.add(achievement)
    else:
        for key, value in payload.model_dump().items():
            setattr(achievement, key, value)
    record_audit(db, request, admin, action, "achievement", slug, {"xp_reward": payload.xp_reward})
    db.commit()
    return achievement_summary(db, achievement)


@router.get("/xp-transactions", response_model=list[AdminXPTransactionRead])
def xp_transactions(
    db: DB, admin: Admin, limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    del admin
    rows = db.execute(select(XPTransaction, User.username).join(
        User, User.id == XPTransaction.user_id,
    ).order_by(XPTransaction.created_at.desc()).limit(limit).offset(offset)).all()
    return [{
        "id": item.id, "username": username, "amount": item.amount, "reason": item.reason,
        "source_type": item.source_type, "source_id": item.source_id, "created_at": item.created_at,
    } for item, username in rows]


@router.get("/rank-history", response_model=list[AdminRankHistoryRead])
def rank_history(
    db: DB, admin: Admin, limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    del admin
    rows = db.execute(select(RankHistory, User.username).join(
        User, User.id == RankHistory.user_id,
    ).order_by(RankHistory.reached_at.desc()).limit(limit).offset(offset)).all()
    return [{
        "id": item.id, "username": username, "rank_slug": item.rank_slug, "reached_at": item.reached_at,
    } for item, username in rows]


@router.get("/audit-logs", response_model=list[AuditLogRead])
def audit_logs(
    db: DB, admin: Admin, limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    del admin
    actor = User.__table__.alias("audit_actor")
    rows = db.execute(select(AuditLog, actor.c.username).outerjoin(
        actor, actor.c.id == AuditLog.actor_user_id,
    ).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).offset(offset)).all()
    return [{
        "id": item.id, "actor_user_id": item.actor_user_id, "actor_username": username,
        "action": item.action, "target_type": item.target_type, "target_id": item.target_id,
        "details": item.details, "ip_address": item.ip_address, "created_at": item.created_at,
    } for item, username in rows]
