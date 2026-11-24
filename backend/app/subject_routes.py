"""Live subject-level discovery, including audited legacy curriculum mapping."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .access_control import audience_filter
from .auth import OptionalUser
from .main_dependencies import get_db
from .models import Problem
from .subject_catalog import SUBJECTS, matched_subject_ids

router = APIRouter(tags=["subjects"])
DB = Annotated[Session, Depends(get_db)]

@router.get("/subjects")
def subject_catalog(db: DB, viewer: OptionalUser = None) -> dict:
    # Respect publication + individual learner access in the backend, not the UI.
    visible = db.scalars(
        select(Problem).where(
            Problem.status == "PUBLISHED",
            audience_filter(Problem, "problem", viewer),
        )
    ).all()
    counts: dict[int, int] = {subject["id"]: 0 for subject in SUBJECTS}
    classified_slugs: set[str] = set()
    for problem in visible:
        matched = matched_subject_ids(problem)
        for subject_id in matched:
            counts[subject_id] += 1
        if matched:
            classified_slugs.add(problem.slug)
    result = [{
        **item,
        "published_questions": counts[item["id"]],
        "remaining_to_target": max(0, item["target"] - counts[item["id"]]),
        "execution_status": ("Existing practice + knowledge checks" if counts[item["id"]] > 3
                             else "Knowledge checks" if counts[item["id"]] else "Not yet evaluated"),
    } for item in SUBJECTS]
    return {
        "subjects": result,
        "target_total": sum(item["target"] for item in SUBJECTS),
        "classified_published": len(classified_slugs),
        "published_catalog_total": len(visible),
        "unclassified_legacy": len(visible) - len(classified_slugs),
        "classification_note": "Legacy logic, NumPy, Pandas and data-analysis questions are mapped to their subjects. Other legacy questions may remain unclassified. Some subjects offer knowledge checks only, not specialized code runtimes.",
    }
