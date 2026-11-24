"""The 45 subject catalogue is real, safely scoped and accurately counted."""
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.database import Base
from app.main import app, get_db
from app.seed import seed
from app.models import LearningPath, LearningPathProblem, Problem, ProblemEvaluator, TestCase
from app.subject_catalog import SUBJECTS


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'subjects.db'}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            seed(session)
            yield session
    finally:
        engine.dispose()


@pytest.fixture
def client(db):
    def override():
        with Session(db.get_bind()) as session:
            yield session
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_source_catalogue_is_complete_and_targets_are_auditable():
    assert len(SUBJECTS) == 45
    assert [s["id"] for s in SUBJECTS] == list(range(1, 46))
    assert len({s["slug"] for s in SUBJECTS}) == 45
    assert sum(s["target"] for s in SUBJECTS) == 2500
    assert all(s["target"] >= 30 for s in SUBJECTS)


def test_each_subject_has_three_genuine_evaluated_checks(db):
    for subject in SUBJECTS:
        problems = db.scalars(select(Problem).where(
            Problem.topic == subject["name"], Problem.status == "PUBLISHED",
            Problem.format == "MULTIPLE_CHOICE",
        )).all()
        assert len(problems) >= 3, subject["name"]
        ours = [p for p in problems if f'Subject:{subject["slug"]}' in p.tags]
        assert len(ours) == 3, subject["name"]
        path = db.get(LearningPath, "subject-" + subject["slug"][:65])
        assert path is not None
        assert path.status == "PUBLISHED" and path.access_scope == "ALL"
        members = db.scalars(select(LearningPathProblem).where(
            LearningPathProblem.path_slug == path.slug
        )).all()
        assert len(members) == 3
        for problem in ours:
            assert problem.access_scope == "ALL"
            assert len(problem.choices) == 4 and len(set(problem.choices)) == 4
            assert problem.starters == []
            assert problem.description.strip().endswith("?") or problem.description.strip().endswith(".")
            evaluator = db.get(ProblemEvaluator, problem.slug)
            assert evaluator.kind == "multiple_choice"
            tests = db.scalars(select(TestCase).where(TestCase.problem_slug == problem.slug)).all()
            assert len(tests) == 1 and tests[0].is_hidden
            assert json.loads(tests[0].expected_output) in problem.choices


def test_subject_catalogue_api_respects_public_audience(client):
    response = client.get("/api/v1/subjects")
    assert response.status_code == 200
    payload = response.json()
    assert payload["target_total"] == 2500
    assert len(payload["subjects"]) == 45
    assert payload["classified_published"] == 352
    assert payload["published_catalog_total"] == 372
    assert sum(entry["published_questions"] for entry in payload["subjects"]) == 352
    assert all(entry["remaining_to_target"] >= 0 for entry in payload["subjects"])
    assert payload["unclassified_legacy"] == 20
    indexed = {s["id"]: s for s in payload["subjects"]}
    assert indexed[1]["published_questions"] == 105
    assert indexed[5]["published_questions"] == 53
    assert indexed[6]["published_questions"] == 53
    assert indexed[7]["published_questions"] == 18
    assert indexed[1]["remaining_to_target"] == 0


def test_no_repeated_new_titles_or_quiz_statements(db):
    subjects = [item["name"] for item in SUBJECTS]
    problems = list(db.scalars(select(Problem).where(Problem.topic.in_(subjects))))
    owned = [p for p in problems if any(t.startswith("Subject:") for t in p.tags)]
    assert len(owned) == 135
    assert len({p.title.casefold() for p in owned}) == 135
    assert len({p.description.casefold() for p in owned}) == 135
