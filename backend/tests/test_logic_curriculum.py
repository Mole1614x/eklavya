"""The Logic Building curriculum is real judge-backed content, not placeholder cards."""
from collections import Counter
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.database import Base
from app.models import LearningPath, LearningPathProblem, Problem, TestCase
from app.seed import seed

EXISTING_EQUIVALENTS = {
    1: "parity-check",
    17: "sum-of-digits",
    91: "pair-indices",
    92: "balanced-delimiters",
}

LEVEL_SIZES = {1: 15, 2: 20, 3: 10, 4: 15, 5: 20, 6: 10, 7: 10}


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'curriculum.db'}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            seed(session)
            yield session
    finally:
        engine.dispose()


def test_logic_curriculum_has_seven_ordered_levels_and_real_judge_cases(db):
    problems = list(db.scalars(select(Problem)))
    assert len(problems) == 2527  # original 26 + 96 logic + 115 data practice
    assert Counter(problem.category for problem in problems)["foundations"] == 50
    assert Counter(problem.category for problem in problems)["code"] == 101
    level_problems = {
        n: list(db.scalars(select(LearningPathProblem)
            .where(LearningPathProblem.path_slug == f"logic-level-{n}")
            .order_by(LearningPathProblem.position)))
        for n in LEVEL_SIZES
    }
    for level, expected_count in LEVEL_SIZES.items():
        path = db.get(LearningPath, f"logic-level-{level}")
        assert path is not None and path.status == "PUBLISHED" and path.access_scope == "ALL"
        assignments = level_problems[level]
        assert len(assignments) == expected_count
        assert [entry.position for entry in assignments] == list(range(1, expected_count + 1))
        for assignment in assignments:
            problem = db.get(Problem, assignment.problem_slug)
            assert problem is not None and problem.status == "PUBLISHED"
            assert problem.access_scope == "ALL"
            assert problem.format == "CODE"
            assert problem.starters
            assert len(problem.test_cases) >= 2
            assert any(not case.is_hidden for case in problem.test_cases)
            assert any(case.is_hidden for case in problem.test_cases)
            assert problem.examples[0]["output"]
    assert level_problems[1][0].problem_slug == EXISTING_EQUIVALENTS[1]
    assert level_problems[2][1].problem_slug == EXISTING_EQUIVALENTS[17]
    assert level_problems[7][0].problem_slug == EXISTING_EQUIVALENTS[91]
    assert level_problems[7][1].problem_slug == EXISTING_EQUIVALENTS[92]
    assert len({entry.problem_slug for assignments in level_problems.values() for entry in assignments}) == 100


def test_logic_seed_is_idempotent(db):
    initial = db.scalar(select(Problem.slug).where(Problem.slug == "diamond-star-pattern"))
    assert initial == "diamond-star-pattern"
    assert seed(db) == 2527
    assert len(list(db.scalars(select(TestCase).where(TestCase.problem_slug == "diamond-star-pattern")))) == 2
