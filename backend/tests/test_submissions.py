import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.main import app
from app.main_dependencies import get_db
from app.models import Submission, TestCase as ProblemTestCase, User
from app.seed import seed


@pytest.fixture
def submission_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'submissions.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)

    def override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            registration = client.post("/api/v1/auth/register", json={
                "email": "solver@example.com", "username": "solver", "password": "StrongPass123", "display_name": "Solver",
            }).json()
            yield client, engine, {"Authorization": f"Bearer {registration['access_token']}"}
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_submission_is_queued_and_source_is_not_returned(submission_client):
    client, engine, headers = submission_client
    response = client.post("/api/v1/problems/parity-check/submissions", headers=headers, json={
        "language": "python", "source_code": "print('Even')", "mode": "SUBMIT",
    })
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert "source_code" not in response.json()
    history = client.get("/api/v1/submissions", headers=headers).json()
    assert [item["id"] for item in history] == [response.json()["id"]]
    with Session(engine) as db:
        assert db.scalar(select(Submission)).source_code == "print('Even')"


def test_language_ownership_and_hidden_test_isolation(submission_client):
    client, _, headers = submission_client
    assert client.post("/api/v1/problems/parity-check/submissions", headers=headers, json={"language": "ruby", "source_code": "puts 1"}).status_code == 422
    assert client.get("/api/v1/submissions").status_code == 401
    public = client.get("/api/v1/problems/parity-check").json()
    assert "test_cases" not in public
    assert "expected_output" not in str(public)


def test_admin_problem_management_rejects_learner(submission_client):
    client, engine, headers = submission_client
    payload = {
        "title": "Managed", "category": "code", "difficulty": "Easy", "format": "CODE", "topic": "Testing",
        "tags": ["Testing"], "description": "Managed problem", "constraints": [], "examples": [],
        "test_cases": [{"input_data": "1", "expected_output": "1", "is_hidden": True}],
    }
    assert client.put("/api/v1/admin/problems/managed", headers=headers, json=payload).status_code == 403
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.username == "solver"))
        user.role = "admin"
        db.commit()
    assert client.put("/api/v1/admin/problems/managed", headers=headers, json=payload).status_code == 204
    with Session(engine) as db:
        case = db.scalar(select(ProblemTestCase).where(ProblemTestCase.problem_slug == "managed"))
        assert case.is_hidden is True
