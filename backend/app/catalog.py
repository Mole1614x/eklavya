from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .access_control import audience_filter
from .models import Problem, User
from .schemas import Catalog, Category, Difficulty, ProblemSummary
from .subject_catalog import subject_clause


def list_problems(
    db: Session, search: str, category: Category | None, difficulty: Difficulty | None,
    topic: str | None, limit: int, offset: int, viewer: User | None = None, subject: str | None = None,
) -> Catalog:
    filters = [Problem.status == "PUBLISHED", audience_filter(Problem, "problem", viewer)]
    if category:
        filters.append(Problem.category == category)
    topics = db.scalars(select(Problem.topic).where(*filters).distinct().order_by(Problem.topic)).all()
    if subject:
        filters.append(subject_clause(subject))
    if difficulty:
        filters.append(Problem.difficulty == difficulty)
    if topic:
        filters.append(Problem.topic == topic)
    if search.strip():
        term = search.strip().lower()
        filters.append(
            func.lower(Problem.title).contains(term, autoescape=True)
            | func.lower(Problem.topic).contains(term, autoescape=True)
        )
    total = db.scalar(select(func.count()).select_from(Problem).where(*filters))
    columns = [getattr(Problem, name) for name in ProblemSummary.model_fields]
    rows = db.execute(
        select(*columns).where(*filters).order_by(Problem.title, Problem.slug).limit(limit).offset(offset)
    ).mappings()
    return Catalog(items=[ProblemSummary.model_validate(row) for row in rows], total=total or 0, topics=list(topics))
