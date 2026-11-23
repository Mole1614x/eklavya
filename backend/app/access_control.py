"""Centralized, database-backed student audience rules.

Never use client-side hiding as an authorization boundary. Public list and
detail handlers must apply audience_filter; mutations and execution paths must
call can_access. Existing assessment group grants remain supported.
"""
from __future__ import annotations

from typing import Literal

from fastapi import HTTPException
from sqlalchemy import and_, delete, exists, or_, select, true
from sqlalchemy.orm import Session

from .models import (
    Assessment, AssessmentAssignment, AssessmentGroupAssignment, ContentAssignment,
    Contest, LearnerGroupMember, LearningPath, PracticeDataset, Problem, User,
)

AccessScope = Literal["ALL", "SELECTED"]
CONTENT_MODELS = {
    "problem": (Problem, "slug"),
    "contest": (Contest, "slug"),
    "path": (LearningPath, "slug"),
    "dataset": (PracticeDataset, "id"),
    "assessment": (Assessment, "id"),
}


def target(db: Session, kind: str, identifier: str):
    definition = CONTENT_MODELS.get(kind)
    if definition is None:
        raise HTTPException(404, detail="Content type not found")
    model, key = definition
    return db.scalar(select(model).where(getattr(model, key) == identifier))


def audience_filter(model, kind: str, user: User | None):
    """Composable SQL predicate; safe for listings without N+1 checks."""
    if user is not None and user.role == "admin":
        return true()
    if user is None or user.role != "learner" or not user.is_active:
        return model.access_scope == "ALL"
    if kind == "assessment":
        direct = exists(select(AssessmentAssignment.id).where(
            AssessmentAssignment.assessment_id == model.id,
            AssessmentAssignment.user_id == user.id,
        ))
        group = exists(select(AssessmentGroupAssignment.assessment_id).join(
            LearnerGroupMember,
            LearnerGroupMember.group_id == AssessmentGroupAssignment.group_id,
        ).where(
            AssessmentGroupAssignment.assessment_id == model.id,
            LearnerGroupMember.user_id == user.id,
        ))
        return or_(model.access_scope == "ALL", direct, group)
    key = CONTENT_MODELS[kind][1]
    grant = exists(select(ContentAssignment.id).where(
        ContentAssignment.content_type == kind,
        ContentAssignment.content_id == getattr(model, key),
        ContentAssignment.user_id == user.id,
    ))
    return or_(model.access_scope == "ALL", grant)


def can_access(db: Session, item, kind: str, user: User | None) -> bool:
    if user is not None and user.role == "admin":
        return True
    if item is None:
        return False
    if user is None or user.role != "learner" or not user.is_active:
        return item.access_scope == "ALL"
    model, key = CONTENT_MODELS[kind]
    identifier = getattr(item, key)
    return db.scalar(select(getattr(model, key)).where(
        getattr(model, key) == identifier, audience_filter(model, kind, user),
    )) is not None


def student_ids(db: Session, kind: str, identifier: str) -> list[int]:
    if kind == "assessment":
        query = select(AssessmentAssignment.user_id).where(AssessmentAssignment.assessment_id == identifier)
    else:
        query = select(ContentAssignment.user_id).where(
            ContentAssignment.content_type == kind,
            ContentAssignment.content_id == identifier,
        )
    return sorted(set(db.scalars(query)))


def assignment_count(db: Session, kind: str, identifier: str) -> int:
    if kind == "assessment":
        direct = exists(select(AssessmentAssignment.id).where(
            AssessmentAssignment.assessment_id == identifier,
        ))
        groups = exists(select(AssessmentGroupAssignment.assessment_id).where(
            AssessmentGroupAssignment.assessment_id == identifier,
        ))
        return int(bool(db.scalar(select(direct)))) + int(bool(db.scalar(select(groups))))
    return len(student_ids(db, kind, identifier))


def validate_students(db: Session, identifiers: list[int]) -> None:
    if len(identifiers) != len(set(identifiers)) or len(identifiers) > 1000:
        raise HTTPException(422, detail="Student assignments must be unique and limited to 1000")
    if not identifiers:
        return
    valid = set(db.scalars(select(User.id).where(
        User.id.in_(identifiers), User.role == "learner", User.is_active.is_(True),
    )))
    if valid != set(identifiers):
        raise HTTPException(422, detail="Select registered, active learner accounts only")


def replace_students(db: Session, kind: str, identifier: str, identifiers: list[int]) -> None:
    validate_students(db, identifiers)
    if kind == "assessment":
        db.execute(delete(AssessmentAssignment).where(AssessmentAssignment.assessment_id == identifier))
        db.add_all(AssessmentAssignment(assessment_id=identifier, user_id=value) for value in identifiers)
    else:
        db.execute(delete(ContentAssignment).where(
            ContentAssignment.content_type == kind,
            ContentAssignment.content_id == identifier,
        ))
        db.add_all(ContentAssignment(
            content_type=kind, content_id=identifier, user_id=value,
        ) for value in identifiers)
    db.flush()


def require_publishable(db: Session, item, kind: str) -> None:
    if item.access_scope == "SELECTED":
        model, key = CONTENT_MODELS[kind]
        if not assignment_count(db, kind, str(getattr(item, key))):
            raise HTTPException(
                status_code=409,
                detail="Assign at least one student or group when access is SELECTED",
            )


def access_summary(db: Session, item, kind: str) -> dict:
    model, key = CONTENT_MODELS[kind]
    identifier = str(getattr(item, key))
    return {
        "access_scope": item.access_scope,
        "assigned_user_ids": student_ids(db, kind, identifier),
        "assigned_count": assignment_count(db, kind, identifier),
        "published": (
            item.status == "PUBLISHED"
            if kind in ("problem", "path", "assessment", "dataset")
            else item.publication_status == "PUBLISHED"
        ),
    }
