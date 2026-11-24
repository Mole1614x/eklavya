from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from .access_control import audience_filter
from .models import Problem, Submission, User
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


# Shared sorting contract: all filtered pages and Previous/Next use the same order.
DIFFICULTY_ORDER = case(
    (Problem.difficulty == "Beginner", 0),
    (Problem.difficulty == "Easy", 1),
    (Problem.difficulty == "Medium", 2),
    (Problem.difficulty == "Hard", 3),
    else_=4,
)


def catalog_order():
    return (DIFFICULTY_ORDER, Problem.title, Problem.slug)


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
        select(*columns).where(*filters).order_by(*catalog_order()).limit(limit).offset(offset)
    ).mappings().all()
    items = [ProblemSummary.model_validate(row) for row in rows]
    solved_slugs: list[str] = []
    if viewer is not None and items:
        visible_slugs = [item.slug for item in items]
        solved_slugs = list(db.scalars(select(Submission.problem_slug).where(
            Submission.user_id == viewer.id,
            Submission.problem_slug.in_(visible_slugs),
            Submission.mode == "SUBMIT",
            Submission.status == "FINISHED",
            Submission.verdict == "ACCEPTED",
        ).distinct()))
    return Catalog(items=items, total=total or 0, topics=list(topics), solved_slugs=solved_slugs)


def problem_neighbors(
    db: Session, slug: str, search: str, category: Category | None, difficulty: Difficulty | None,
    topic: str | None, viewer: User | None, subject: str | None,
) -> dict[str, str | int | None] | None:
    """Find adjacent visible questions in the exact order used by the catalog.

    Queries are bounded and don't fetch/serialize the entire question bank.
    A missing or filtered-out slug never yields another learner's private titles.
    """
    filters = problem_filters(search, category, difficulty, topic, viewer, subject)
    current = db.execute(
        select(Problem.title, Problem.slug, Problem.difficulty)
        .where(*filters, Problem.slug == slug)
    ).first()
    if current is None:
        return None
    title, current_slug, difficulty = current
    # Compare difficulty ranks first, then the same title+slug tie breakers
    # used by the listing. This preserves cross-page navigation exactly.
    rank = {"Beginner": 0, "Easy": 1, "Medium": 2, "Hard": 3}[difficulty]
    before_name = or_(Problem.title < title, and_(Problem.title == title, Problem.slug < current_slug))
    after_name = or_(Problem.title > title, and_(Problem.title == title, Problem.slug > current_slug))
    prior = or_(DIFFICULTY_ORDER < rank, and_(DIFFICULTY_ORDER == rank, before_name))
    after = or_(DIFFICULTY_ORDER > rank, and_(DIFFICULTY_ORDER == rank, after_name))
    previous = db.scalar(
        select(Problem.slug).where(*filters, prior)
        .order_by(DIFFICULTY_ORDER.desc(), Problem.title.desc(), Problem.slug.desc()).limit(1)
    )
    following = db.scalar(
        select(Problem.slug).where(*filters, after)
        .order_by(*catalog_order()).limit(1)
    )
    position = (db.scalar(select(func.count()).select_from(Problem).where(*filters, prior)) or 0) + 1
    total = db.scalar(select(func.count()).select_from(Problem).where(*filters)) or 0
    return {"previous": previous, "next": following, "position": position, "total": total}
