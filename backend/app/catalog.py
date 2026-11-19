from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Problem
from .schemas import Catalog, Category, Difficulty, ProblemSummary


def list_problems(
    db: Session, search: str, category: Category | None, difficulty: Difficulty | None,
    topic: str | None, limit: int, offset: int,
) -> Catalog:
    filters = [Problem.status == "PUBLISHED"]
    if category:
        filters.append(Problem.category == category)
    topics = db.scalars(select(Problem.topic).where(*filters).distinct().order_by(Problem.topic)).all()
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
