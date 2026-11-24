from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.database import Base
from app.main import app, get_db
from app.models import Problem, Profile, Submission, User
from app.seed import seed
from app.catalog import list_problems
from app.knowledge_difficulty import knowledge_difficulty


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'tests.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        yield session
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
        app.dependency_overrides.pop(get_db)


def test_health_without_database():
    assert TestClient(app).get("/api/v1/health").json() == {"status": "ok", "service": "eklavya-api"}


def test_catalog_preserves_domain_coverage(client):
    response = client.get("/api/v1/problems", params={"limit": 100})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2531
    # Check a bounded page while preserving the expanded catalog total.
    items = payload["items"]
    assert len(items) == 100
    assert len({item["slug"] for item in items}) == 100
    assert all(item["format"] in {
        "CODE", "EXPRESSION", "SQL_QUERY", "NUMERICAL", "MULTIPLE_CHOICE", "DATASET_ANALYSIS",
    } for item in items)


def test_filters_and_pagination(client):
    response = client.get("/api/v1/problems", params={
        "q": "Star Staircase", "category": "foundations", "difficulty": "Beginner", "topic": "Patterns",
    })
    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["star-staircase"]

    results = client.get("/api/v1/problems", params={"category": "foundations", "q": "parity", "limit": 1, "offset": 0}).json()
    assert results["total"] == 1
    assert [item["title"] for item in results["items"]] == ["Parity Check"]
    assert client.get("/api/v1/problems", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/v1/problems", params={"difficulty": "Impossible"}).status_code == 422


def test_detail_exposes_only_public_examples_and_starters(client):
    result = client.get("/api/v1/problems/hollow-square").json()
    assert result["examples"][0]["output"] == "****\n*  *\n*  *\n****"
    assert {starter["language"] for starter in result["starters"]} == {"python", "java", "c", "cpp"}
    assert "hidden_tests" not in result
    assert client.get("/api/v1/problems/does-not-exist").status_code == 404


def test_seed_can_run_twice(db):
    assert seed(db) == 2531
    assert len(db.scalars(select(Problem)).all()) == 2531
    assert len(db.get(Problem, "parity-check").starters) == 4


def test_difficulty_constraint(db):
    db.get(Problem, "parity-check").difficulty = "Invalid"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_database_outage_returns_generic_error():
    def broken_db():
        raise OperationalError("internal SQL", {}, Exception("internal details"))

    app.dependency_overrides[get_db] = broken_db
    try:
        response = TestClient(app).get("/api/v1/problems")
        assert response.status_code == 503
        assert response.json()["detail"] == "The service is temporarily unavailable"
        assert response.json()["request_id"] == response.headers["x-request-id"]
    finally:
        app.dependency_overrides.pop(get_db)


def test_problem_navigation_uses_catalog_order_and_page_boundaries(client):
    first_page = client.get("/api/v1/problems", params={"limit": 2}).json()
    first, second = first_page["items"]
    first_nav = client.get(f"/api/v1/problems/{first['slug']}/navigation")
    assert first_nav.status_code == 200
    assert first_nav.json() == {
        "previous": None, "next": second["slug"], "position": 1, "total": 2531,
    }
    second_nav = client.get(f"/api/v1/problems/{second['slug']}/navigation")
    assert second_nav.json()["previous"] == first["slug"]
    assert second_nav.json()["position"] == 2

    # Navigation continues across 50-question catalogue pages.
    last_of_page = client.get("/api/v1/problems", params={"limit": 1, "offset": 49}).json()["items"][0]
    first_of_next = client.get("/api/v1/problems", params={"limit": 1, "offset": 50}).json()["items"][0]
    assert client.get(f"/api/v1/problems/{last_of_page['slug']}/navigation").json()["next"] == first_of_next["slug"]
    assert client.get(f"/api/v1/problems/{first_of_next['slug']}/navigation").json()["previous"] == last_of_page["slug"]

    last = client.get("/api/v1/problems", params={"limit": 1, "offset": 2530}).json()["items"][0]
    last_nav = client.get(f"/api/v1/problems/{last['slug']}/navigation").json()
    assert last_nav["next"] is None
    assert last_nav["position"] == 2531
    assert last_nav["total"] == 2531


def test_problem_navigation_respects_filters_and_does_not_leak_unknown_problems(client):
    single = client.get("/api/v1/problems/star-staircase/navigation", params={
        "category": "foundations", "difficulty": "Beginner", "topic": "Patterns",
        "q": "Star Staircase",
    })
    assert single.status_code == 200
    assert single.json() == {"previous": None, "next": None, "position": 1, "total": 1}

    # The same slug can be viewed directly but is not part of unrelated filtered results.
    assert client.get("/api/v1/problems/parity-check/navigation", params={"q": "Star Staircase"}).status_code == 404
    assert client.get("/api/v1/problems/does-not-exist/navigation").status_code == 404
    assert client.get("/api/v1/problems/parity-check/navigation", params={"subject": "not-a-subject"}).status_code == 422

    subjects = client.get("/api/v1/problems", params={"subject": "numpy", "limit": 2}).json()
    assert len(subjects["items"]) == 2
    first, second = subjects["items"]
    neighbors = client.get(f"/api/v1/problems/{first['slug']}/navigation", params={"subject": "numpy"}).json()
    assert neighbors["previous"] is None
    assert neighbors["next"] == second["slug"]
    assert neighbors["total"] == subjects["total"]



def test_catalog_orders_beginner_easy_medium_hard_and_navigation_matches(client):
    levels = {"Beginner": 0, "Easy": 1, "Medium": 2, "Hard": 3}
    first = client.get("/api/v1/problems", params={"limit": 100}).json()["items"]
    next_page = client.get("/api/v1/problems", params={"limit": 100, "offset": 100}).json()["items"]
    scores = [levels[item["difficulty"]] for item in first + next_page]
    assert scores == sorted(scores)

    # Both listing and navigation agree even across a difficulty-tier boundary.
    expected = []
    for offset in range(0, 2531, 100):
        expected.extend(client.get("/api/v1/problems", params={"limit": 100, "offset": offset}).json()["items"])
    assert len(expected) == 2531
    assert set(item["difficulty"] for item in expected) == set(levels)
    assert [levels[item["difficulty"]] for item in expected] == sorted(
        levels[item["difficulty"]] for item in expected
    )
    for index in (0, 49, 50, 200, 201, 500, 1000, 1500, 2000, 2530):
        current = expected[index]
        neighbors = client.get(f"/api/v1/problems/{current['slug']}/navigation").json()
        assert neighbors["position"] == index + 1
        assert neighbors["previous"] == (expected[index - 1]["slug"] if index else None)
        assert neighbors["next"] == (expected[index + 1]["slug"] if index + 1 < len(expected) else None)


def test_knowledge_check_difficulty_comes_from_skill_not_hardcoded_easy(db):
    levels = set(db.scalars(select(Problem.difficulty).where(Problem.format == "MULTIPLE_CHOICE")).all())
    assert levels == {"Beginner", "Easy", "Medium", "Hard"}
    assert knowledge_difficulty(
        {"skill": "Array left-rotation 5", "prompt": "An array is rotated left twice."},
        "comprehensive_mcq_05_calculated.json",
    ) == "Beginner"
    assert knowledge_difficulty(
        {"skill": "F1 calculation 21", "prompt": "Calculate F1 using precision and recall."},
        "comprehensive_mcq_05_calculated.json",
    ) == "Hard"
    assert knowledge_difficulty(
        {"skill": "AdamW optimizer", "prompt": "Identify the technique."},
        "comprehensive_mcq_06b.json",
    ) == "Medium"
    assert knowledge_difficulty(
        {"skill": "Operator precedence", "prompt": "2 + 3 * 4?", "difficulty": "Hard"},
        "comprehensive_mcq_01.json",
    ) == "Hard"


def test_solved_badges_require_own_accepted_finished_submit(db):
    user = User(
        email="solves@example.com", username="solves", password_hash="unused",
        profile=Profile(display_name="Solves"),
    )
    another = User(
        email="other@example.com", username="other", password_hash="unused",
        profile=Profile(display_name="Other"),
    )
    db.add_all([user, another])
    db.flush()
    db.add_all([
        Submission(id="solved-parity", user_id=user.id, problem_slug="parity-check",
                   language="python", source_code="pass", mode="SUBMIT",
                   status="FINISHED", verdict="ACCEPTED"),
        Submission(id="only-run", user_id=user.id, problem_slug="star-staircase",
                   language="python", source_code="", mode="RUN",
                   status="FINISHED", verdict="ACCEPTED"),
        Submission(id="failed-submit", user_id=user.id, problem_slug="sum-of-digits",
                   language="python", source_code="", mode="SUBMIT",
                   status="FINISHED", verdict="WRONG_ANSWER"),
        Submission(id="queued-submit", user_id=user.id, problem_slug="hollow-square",
                   language="python", source_code="", mode="SUBMIT",
                   status="QUEUED", verdict=None),
        Submission(id="other-users-solve", user_id=another.id, problem_slug="star-staircase",
                   language="python", source_code="", mode="SUBMIT",
                   status="FINISHED", verdict="ACCEPTED"),
    ])
    db.flush()
    for name, should_be_solved in (
        ("parity-check", True), ("star-staircase", False),
        ("sum-of-digits", False), ("hollow-square", False),
    ):
        result = list_problems(
            db, search=name.replace("-", " "), category=None,
            difficulty=None, topic=None, limit=50, offset=0, viewer=user,
        )
        assert (name in result.solved_slugs) is should_be_solved
    public = list_problems(db, "", None, None, None, 100, 0)
    assert public.solved_slugs == []
