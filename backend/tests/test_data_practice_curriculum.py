"""Curated data science practice uses real functions, not title-only placeholders."""
import ast
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models import LearningPath, LearningPathProblem, Problem, ProblemEvaluator, TestCase
from app.seed import seed

PACK_COUNTS = {"numpy": 50, "pandas": 50, "data_analysis": 15}


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'data-practice.db'}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            seed(session)
            yield session
    finally:
        engine.dispose()


def test_data_science_curriculum_has_115_distinct_runnable_items(db):
    observed = set()
    for pack, expected in PACK_COUNTS.items():
        path = settings().seed_file.parent / f"{pack}_practice.json"
        items = json.loads(path.read_text(encoding="utf-8"))
        assert len(items) == expected
        assert [item["number"] for item in items] == list(range(1, expected + 1))
        for item in items:
            slug = item["slug"]
            assert slug not in observed
            observed.add(slug)
            ast.parse(item["reference_source"], filename=f"{slug}.py")
            problem = db.get(Problem, slug)
            evaluator = db.get(ProblemEvaluator, slug)
            assert problem is not None and evaluator is not None
            assert evaluator.kind == "data_practice_function"
            assert evaluator.config["reference_source"] == item["reference_source"]
            assert problem.status == "PUBLISHED" and problem.access_scope == "ALL"
            assert problem.category == "data" and problem.format == "CODE"
            assert len(problem.starters) == 1 and problem.starters[0].language == "python"
            assert len(problem.test_cases) == 2
            assert [x.is_hidden for x in sorted(problem.test_cases, key=lambda x: x.position)] == [False, True]
            assert all(json.loads(x.input_data) for x in problem.test_cases)
            assert all(x.expected_output == "null" for x in problem.test_cases)
            assert len(problem.description) > 60
        levels = 3 if pack == "data_analysis" else 5
        for level in range(1, levels + 1):
            prefix = pack.replace("_", "-")
            slug = f"{prefix}-practice-{level}"
            learning_path = db.get(LearningPath, slug)
            assert learning_path is not None and learning_path.status == "PUBLISHED"
            members = list(db.scalars(select(LearningPathProblem).where(
                LearningPathProblem.path_slug == slug
            ).order_by(LearningPathProblem.position)))
            assert len(members) == 5 if pack == "data_analysis" else len(members) == 10
    assert len(observed) == 115
    assert seed(db) == 2531


def test_data_practice_is_not_exposed_through_problem_detail(db):
    problem = db.get(Problem, "numpy-create-array")
    evaluator = db.get(ProblemEvaluator, problem.slug)
    assert evaluator.config["reference_source"]
    assert "reference_source" not in problem.description
    assert all("reference_source" not in starter.code for starter in problem.starters)
