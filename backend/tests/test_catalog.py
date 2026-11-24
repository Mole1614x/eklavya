from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.database import Base
from app.main import app, get_db
from app.models import Problem
from app.seed import seed


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
