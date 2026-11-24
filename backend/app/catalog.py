from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from .access_control import audience_filter
from .models import Problem, User
from .schemas import Catalog, Category, Difficulty, ProblemSummary
from .subject_catalog import subject_clause


def problem_filters(
    search: str, category: Category | None, difficulty: Difficulty | None,
    topic: str | None, viewer: User | None, subject: str | None,
) -> list:
    """Apply the same publication, audience and catalog filters to listings and navigation."""
    filters = [Problem.status == "PUBLISHED", audience_filter(Problem, "problem", viewer)]
    if category:
        filters.append(Problem.category == category)
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
    return filters


def list_problems(
    db: Session, search: str, category: Category | None, difficulty: Difficulty | None,
    topic: str | None, limit: int, offset: int, viewer: User | None = None, subject: str | None = None,
) -> Catalog:
    scope = [Problem.status == "PUBLISHED", audience_filter(Problem, "problem", viewer)]
    if category:
        scope.append(Problem.category == category)
    topics = db.scalars(select(Problem.topic).where(*scope).distinct().order_by(Problem.topic)).all()
    filters = problem_filters(search, category, difficulty, topic, viewer, subject)
    total = db.scalar(select(func.count()).select_from(Problem).where(*filters))
    columns = [getattr(Problem, name) for name in ProblemSummary.model_fields]
    rows = db.execute(
        select(*columns).where(*filters).order_by(Problem.title, Problem.slug).limit(limit).offset(offset)
    ).mappings()
    return Catalog(items=[ProblemSummary.model_validate(row) for row in rows], total=total or 0, topics=list(topics))


def problem_neighbors(
    db: Session, slug: str, search: str, category: Category | None, difficulty: Difficulty | None,
    topic: str | None, viewer: User | None, subject: str | None,
) -> dict[str, str | int | None] | None:
    """Find adjacent visible questions in the exact order used by the catalog.

    Queries are bounded and don't fetch/serialize the entire question bank.
    A missing or filtered-out slug never yields another learner's private titles.
    """
    filters = problem_filters(search, category, difficulty, topic, viewer, subject)
    current = db.execute(select(Problem.title, Problem.slug).where(*filters, Problem.slug == slug)).first()
    if current is None:
        return None
    title, current_slug = current
    prior = or_(Problem.title < title, and_(Problem.title == title, Problem.slug < current_slug))
    after = or_(Problem.title > title, and_(Problem.title == title, Problem.slug > current_slug))
    previous = db.scalar(
        select(Problem.slug).where(*filters, prior).order_by(Problem.title.desc(), Problem.slug.desc()).limit(1)
    )
    following = db.scalar(
        select(Problem.slug).where(*filters, after).order_by(Problem.title, Problem.slug).limit(1)
    )
    position = (db.scalar(select(func.count()).select_from(Problem).where(*filters, prior)) or 0) + 1
    total = db.scalar(select(func.count()).select_from(Problem).where(*filters)) or 0
    return {"previous": previous, "next": following, "position": position, "total": total}
