import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.main import app
from app.main_dependencies import get_db
from app.models import AccountToken, RefreshToken, User


@pytest.fixture
def auth_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    Base.metadata.create_all(engine)

    def override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def registration():
    return {"email": "Learner@Example.com", "username": "Learner_1", "password": "StrongPass123", "display_name": "Learner"}


def test_registration_login_profile_refresh_and_logout(auth_client):
    client, engine = auth_client
    registered = client.post("/api/v1/auth/register", json=registration())
    assert registered.status_code == 201
    tokens = registered.json()
    access = tokens["access_token"]

    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert profile.json()["email"] == "learner@example.com"
    assert profile.json()["profile"]["display_name"] == "Learner"
    assert client.patch("/api/v1/auth/me", json={"bio": "Building every day"}, headers={"Authorization": f"Bearer {access}"}).json()["profile"]["bio"] == "Building every day"

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    new_refresh = refreshed.json()["refresh_token"]
    assert client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh}).status_code == 401

    login = client.post("/api/v1/auth/login", json={"identity": "learner_1", "password": "StrongPass123"})
    assert login.status_code == 200
    with Session(engine) as db:
        assert db.scalar(select(User)).password_hash != "StrongPass123"
        assert len(db.scalars(select(RefreshToken)).all()) == 3


def test_uniqueness_validation_and_no_admin_registration(auth_client):
    client, _ = auth_client
    assert client.post("/api/v1/auth/register", json=registration()).status_code == 201
    assert client.post("/api/v1/auth/register", json=registration()).status_code == 409
    weak = registration() | {"email": "other@example.com", "password": "password"}
    assert client.post("/api/v1/auth/register", json=weak).status_code == 422
    public_admin = registration() | {"email": "admin@example.com", "username": "admin", "role": "admin"}
    assert client.post("/api/v1/auth/register", json=public_admin).status_code == 422


def test_verification_and_password_reset_tokens_are_one_time(auth_client):
    client, engine = auth_client
    client.post("/api/v1/auth/register", json=registration())
    with Session(engine) as db:
        verification = db.scalar(select(AccountToken).where(AccountToken.purpose == "verify_email"))
        assert verification is not None

    client.post("/api/v1/auth/password-reset/request", json={"email": "learner@example.com"})
    assert client.post("/api/v1/auth/password-reset/request", json={"email": "missing@example.com"}).status_code == 202
    with Session(engine) as db:
        reset = db.scalar(select(AccountToken).where(AccountToken.purpose == "reset_password"))
        # Tests replace the stored digest with one for a known opaque token to exercise consumption.
        known = "x" * 40
        reset.token_hash = hashlib.sha256(known.encode()).hexdigest()
        db.commit()
    response = client.post("/api/v1/auth/password-reset/confirm", json={"token": known, "password": "NewStrongPass456"})
    assert response.status_code == 204
    with Session(engine) as db:
        assert all(token.revoked_at is not None for token in db.scalars(select(RefreshToken)).all())
    assert client.post("/api/v1/auth/password-reset/confirm", json={"token": known, "password": "NewStrongPass456"}).status_code == 400
    assert client.post("/api/v1/auth/login", json={"identity": "learner_1", "password": "NewStrongPass456"}).status_code == 200
