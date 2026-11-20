from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.main import app
from app.main_dependencies import get_db
from app.judge_client import get_enqueuer
from app.models import Submission, User
from app.seed import seed


@pytest.fixture
def security_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'security.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)

    def override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_enqueuer] = lambda: lambda submission_id: None
    try:
        with TestClient(app) as client:
            tokens = []
            for index in (1, 2):
                response = client.post("/api/v1/auth/register", json={
                    "email": f"security{index}@example.com",
                    "username": f"security{index}",
                    "password": "StrongPass123",
                    "display_name": f"Security {index}",
                })
                tokens.append(response.json()["access_token"])
            yield client, engine, tokens
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def problem_payload() -> dict:
    return {
        "title": "Authorization Probe",
        "category": "foundations",
        "difficulty": "Beginner",
        "format": "CODE",
        "topic": "Security",
        "tags": ["security"],
        "description": "This payload must not bypass administrator authorization.",
        "constraints": [],
        "examples": [],
        "choices": [],
        "test_cases": [],
    }


def test_expired_malformed_and_forged_role_tokens_are_rejected(security_client):
    client, engine, tokens = security_client
    assert client.get("/api/v1/auth/me", headers=bearer("not-a-jwt")).status_code == 401

    with Session(engine) as db:
        user = db.scalar(select(User).where(User.username == "security1"))
        user_id = user.id
    now = datetime.now(timezone.utc)
    expired = jwt.encode({
        "sub": str(user_id), "role": "learner", "type": "access",
        "iat": now - timedelta(hours=1), "exp": now - timedelta(minutes=1),
    }, settings().secret_key, algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers=bearer(expired)).status_code == 401

    forged_role = jwt.encode({
        "sub": str(user_id), "role": "admin", "type": "access", "iat": now,
        "exp": now + timedelta(minutes=5),
    }, settings().secret_key, algorithm="HS256")
    assert client.put(
        "/api/v1/admin/problems/authorization-probe",
        headers=bearer(forged_role), json=problem_payload(),
    ).status_code == 403

    with Session(engine) as db:
        db.get(User, user_id).is_active = False
        db.commit()
    assert client.get("/api/v1/auth/me", headers=bearer(tokens[0])).status_code == 401


def test_cross_user_submission_access_is_concealed(security_client):
    client, _, tokens = security_client
    created = client.post(
        "/api/v1/problems/parity-check/submissions",
        headers=bearer(tokens[0]),
        json={"language": "python", "source_code": "print('Even')", "mode": "SUBMIT"},
    )
    assert created.status_code == 202
    submission_id = created.json()["id"]
    assert client.get(f"/api/v1/submissions/{submission_id}", headers=bearer(tokens[1])).status_code == 404
    assert client.get(f"/api/v1/submissions/{submission_id}", headers=bearer(tokens[0])).status_code == 200
    assert "source_code" not in client.get(f"/api/v1/submissions/{submission_id}", headers=bearer(tokens[0])).json()

    with Session(security_client[1]) as db:
        assert db.get(Submission, submission_id).source_code == "print('Even')"


def test_catalog_search_treats_sql_syntax_as_data(security_client):
    client, _, _ = security_client
    response = client.get("/api/v1/problems", params={"q": "' OR 1=1 --"})
    assert response.status_code == 200
    assert response.json()["total"] == 0
