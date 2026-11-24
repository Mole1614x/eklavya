import json

from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from .config import settings
from .database import Session
from .models import Achievement, Contest, ContestProblem, DailyChallenge, LearningPath, LearningPathProblem, Problem, ProblemEvaluator, RankLevel, StarterCode, TestCase
from .schemas import ProblemDetail


def seed(db: DatabaseSession) -> int:
    # Keep the original catalog stable and load the curated logic packs alongside it.
    # A separate pack prevents overwriting established questions and their judge cases.
    source = json.loads(settings().seed_file.read_text())
    test_cases = json.loads(settings().test_seed_file.read_text()) if settings().test_seed_file.exists() else {}
    logic_ids: dict[int, str] = {}
    seen = {item["slug"] for item in source}
    for pack in sorted(settings().seed_file.parent.glob("logic_levels_*.json")):
        for item in json.loads(pack.read_text()):
            slug = item["slug"]
            if slug in seen:
                raise ValueError(f"Logic catalog slug duplicates existing content: {slug}")
            seen.add(slug)
            logic_ids[item["number"]] = slug
            test_cases[slug] = item["test_cases"]
            source.append({key: value for key, value in item.items() if key not in {"number", "test_cases"}})
    entries = [ProblemDetail.model_validate(item) for item in source]
    evaluators = json.loads(settings().evaluator_seed_file.read_text()) if settings().evaluator_seed_file.exists() else {}
    gamification = json.loads(settings().gamification_seed_file.read_text()) if settings().gamification_seed_file.exists() else {"ranks": [], "achievements": []}
    for rank in gamification["ranks"]:
        db.merge(RankLevel(**rank))
    for achievement in gamification["achievements"]:
        db.merge(Achievement(**achievement))
    for entry in entries:
        problem = db.merge(Problem(
            **entry.model_dump(exclude={"starters"}),
            starters=[StarterCode(**starter.model_dump()) for starter in entry.starters],
        ))
        if entry.slug in test_cases:
            problem.test_cases = [TestCase(**case) for case in test_cases[entry.slug]]
        if entry.slug in evaluators:
            db.merge(ProblemEvaluator(problem_slug=entry.slug, **evaluators[entry.slug]))
    paths = json.loads(settings().learning_paths_seed_file.read_text()) if settings().learning_paths_seed_file.exists() else []
    for path in paths:
        problems = path.pop("problems")
        db.merge(LearningPath(**path))
        for position, problem_slug in enumerate(problems, 1):
            db.merge(LearningPathProblem(path_slug=path["slug"], problem_slug=problem_slug, position=position, milestone="Path complete" if position == len(problems) else None))
    # Structured level-by-level learning paths use the exact problem slugs from the
    # curriculum; existing equivalent problems retain their original identities.
    existing_equivalents = {
        1: "parity-check", 17: "sum-of-digits",
        91: "pair-indices", 92: "balanced-delimiters",
    }
    problem_ids = {**logic_ids, **existing_equivalents}
    levels = [
        (1, "Basic Programming", range(1, 16)),
        (2, "Number-Based Logic", range(16, 36)),
        (3, "Pattern Programming", range(36, 46)),
        (4, "String-Based Logic", range(46, 61)),
        (5, "Arrays and Lists", range(61, 81)),
        (6, "Searching, Sorting and Recursion", range(81, 91)),
        (7, "Interview-Level Logic", range(91, 101)),
    ]
    for number, title, sequence in levels:
        slug = f"logic-level-{number}"
        db.merge(LearningPath(
            slug=slug, title=f"Logic Level {number}: {title}",
            description=f"Guided logic-building practice: {title}. Complete challenges in order.",
            prerequisites=[f"logic-level-{number-1}"] if number > 1 else [],
            status="PUBLISHED", access_scope="ALL",
        ))
        for index, item_number in enumerate(sequence, 1):
            db.merge(LearningPathProblem(
                path_slug=slug, problem_slug=problem_ids[item_number],
                position=index, milestone="Level complete" if index == len(sequence) else None,
            ))
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    if db.scalar(select(DailyChallenge).where(DailyChallenge.challenge_date == today)) is None:
        slugs = [entry.slug for entry in entries]
        db.add(DailyChallenge(challenge_date=today, problem_slug=slugs[today.toordinal() % len(slugs)]))
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    contest_slug = f"weekly-{year}-{week}"
    contest = db.scalar(select(Contest).where(Contest.slug == contest_slug))
    if contest is None:
        from datetime import timedelta
        start = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        contest = Contest(slug=contest_slug, title=f"EKLAVYA Weekly {week}", description="A 90-minute algorithm sprint.", starts_at=start, ends_at=start + timedelta(minutes=90))
        db.add(contest); db.flush()
        for position, problem_slug in enumerate(["pair-indices", "first-occurrence", "balanced-delimiters"], 1):
            db.add(ContestProblem(contest_id=contest.id, problem_slug=problem_slug, position=position, points=100))
    db.commit()
    return len(entries)


if __name__ == "__main__":
    with Session() as db:
        print(f"Seeded {seed(db)} problems")
