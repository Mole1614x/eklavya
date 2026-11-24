"""Live subject-level discovery; counts include only explicitly classified questions."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .access_control import audience_filter
from .auth import OptionalUser
from .main_dependencies import get_db
from .models import Problem
from .subject_catalog import SUBJECTS

router = APIRouter(tags=["subjects"])
DB = Annotated[Session, Depends(get_db)]


@router.get("/subjects")
def subject_catalog(db: DB, viewer: OptionalUser = None) -> dict:
    # SQL aggregation respects role-based ALL/SELECTED audience restrictions.
    rows = db.execute(
        select(Problem.topic, func.count(Problem.slug))
        .where(
            Problem.status == "PUBLISHED",
            audience_filter(Problem, "problem", viewer),
        )
        .group_by(Problem.topic)
    ).all()
    count_by_topic = dict(rows)
    classified = []
    for item in SUBJECTS:
        published = count_by_topic.get(item["name"], 0)
        classified.append({
            **item, "published_questions": published,
            "remaining_to_target": max(0, item["target"] - published),
            "execution_status": "Knowledge checks" if published else "Not yet evaluated",
        })
    return {
        "subjects": classified,
        "target_total": sum(item["target"] for item in SUBJECTS),
        # These tagged counts intentionally do not claim to have classified all
        # 237 pre-existing questions into the new taxonomy.
        "classified_published": sum(item["published_questions"] for item in classified),
        "published_catalog_total": sum(count_by_topic.values()),
        "classification_note": "Existing legacy problems may not yet have a subject tag. Subject counts are conservative and do not imply full execution support.",
    }
