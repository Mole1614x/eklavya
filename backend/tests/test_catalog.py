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
    assert TestClient(app).get("/api/v1/health").json() == {"status": "ok"}


def test_catalog_preserves_domain_coverage(client):
    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 20
    assert Counter(item["category"] for item in payload["items"]) == {
        "foundations": 4, "code": 3, "data": 5, "statistics": 3, "big-data": 2, "ai": 3,
    }
    assert {item["format"] for item in payload["items"]} == {
        "CODE", "EXPRESSION", "SQL_QUERY", "NUMERICAL", "MULTIPLE_CHOICE", "DATASET_ANALYSIS",
    }


def test_filters_and_pagination(client):
    response = client.get("/api/v1/problems", params={
        "q": "star", "category": "foundations", "difficulty": "Beginner", "topic": "Patterns",
    })
    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["star-staircase"]

    results = client.get("/api/v1/problems", params={"category": "foundations", "limit": 1, "offset": 1}).json()
    assert results["total"] == 4
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
    assert seed(db) == 20
    assert len(db.scalars(select(Problem)).all()) == 20
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
        assert response.json() == {"detail": "Catalog is temporarily unavailable"}
    finally:
        app.dependency_overrides.pop(get_db)
