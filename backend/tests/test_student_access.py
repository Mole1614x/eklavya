"""Regression coverage for the shared ALL/SELECTED student-audience contract."""
import base64
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.judge_client import get_dataset_practice_enqueuer, get_enqueuer
from app.main import app
from app.main_dependencies import get_db
from app.models import Assessment, Submission, User
from app.seed import seed


@pytest.fixture
def access_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'student-access.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)

    def override():
        with Session(engine) as db:
            yield db

    original_storage = settings().dataset_storage_dir
    settings().dataset_storage_dir = tmp_path / "datasets"
    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_enqueuer] = lambda: lambda submission_id: None
    app.dependency_overrides[get_dataset_practice_enqueuer] = lambda: lambda run_id: None
    try:
        with TestClient(app) as client:
            headers = {}
            for username in ("admin", "alice", "bob"):
                response = client.post("/api/v1/auth/register", json={
                    "email": f"{username}@example.com", "username": username,
                    "password": "StrongPass123", "display_name": username.capitalize(),
                })
                assert response.status_code == 201
                headers[username] = {"Authorization": f"Bearer {response.json()['access_token']}"}
            with Session(engine) as db:
                db.scalar(select(User).where(User.username == "admin")).role = "admin"
                ids = {user.username: user.id for user in db.scalars(select(User))}
                db.commit()
            yield client, engine, headers, ids
    finally:
        app.dependency_overrides.clear()
        settings().dataset_storage_dir = original_storage
        engine.dispose()


def assessment_definition(scope, ids, status="PUBLISHED"):
    now = datetime.now(timezone.utc)
    return {
        "title": "Scope-aware technical assessment", "assessment_type": "CODING",
        "description": "No individual assignments needed for ALL", "duration_minutes": 30,
        "opens_at": (now - timedelta(minutes=1)).isoformat(),
        "closes_at": (now + timedelta(hours=2)).isoformat(),
        "max_attempts": 1, "release_results": True, "status": status,
        "access_scope": scope, "questions": [{"problem_slug": "parity-check", "points": 100}],
        "assigned_user_ids": ids, "assigned_group_ids": [],
    }


def test_all_assessment_publishes_without_assignments_and_new_student_can_start(access_client):
    client, _, headers, ids = access_client
    response = client.post("/api/v1/advanced/admin/assessments",
                           json=assessment_definition("ALL", []), headers=headers["admin"])
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    assert response.json()["access_scope"] == "ALL"
    assert client.get("/api/v1/advanced/assessments", headers=headers["alice"]).json()[0]["id"] == identifier
    # Question text/slugs are not exposed until an attempt is started.
    assert "problem_slug" not in client.get("/api/v1/advanced/assessments", headers=headers["alice"]).json()[0]["questions"][0]
    newcomer = client.post("/api/v1/auth/register", json={
        "email": "newcomer@example.com", "username": "newcomer",
        "password": "StrongPass123", "display_name": "New Learner",
    })
    fresh = {"Authorization": f"Bearer {newcomer.json()['access_token']}"}
    assert any(item["id"] == identifier for item in client.get("/api/v1/advanced/assessments", headers=fresh).json())
    assert client.post(f"/api/v1/advanced/assessments/{identifier}/start", headers=fresh).status_code == 201


def test_selected_assessment_isolated_and_requires_assignments(access_client):
    client, _, headers, ids = access_client
    missing = client.post("/api/v1/advanced/admin/assessments",
                          json=assessment_definition("SELECTED", []), headers=headers["admin"])
    assert missing.status_code == 409
    created = client.post("/api/v1/advanced/admin/assessments",
                          json=assessment_definition("SELECTED", [ids["alice"]]), headers=headers["admin"])
    assert created.status_code == 201, created.text
    identifier = created.json()["id"]
    assert client.get("/api/v1/advanced/assessments", headers=headers["bob"]).json() == []
    assert client.post(f"/api/v1/advanced/assessments/{identifier}/start", headers=headers["bob"]).status_code == 404
    assert client.post(f"/api/v1/advanced/assessments/{identifier}/start", headers=headers["alice"]).status_code == 201


def test_drafts_are_hidden_even_if_all_and_access_can_change_later(access_client):
    client, _, headers, ids = access_client
    draft = client.post("/api/v1/advanced/admin/assessments",
                        json=assessment_definition("ALL", [], "DRAFT"), headers=headers["admin"])
    assert draft.status_code == 201
    identifier = draft.json()["id"]
    assert client.get("/api/v1/advanced/assessments", headers=headers["bob"]).json() == []
    published = client.patch(f"/api/v1/advanced/admin/assessments/{identifier}/status",
                             json={"status": "PUBLISHED", "reason": "Ready for all learners"},
                             headers=headers["admin"])
    assert published.status_code == 200
    preview = client.post(f"/api/v1/admin/access/assessment/{identifier}/preview",
                          json={"access_scope": "SELECTED", "assigned_user_ids": [ids["alice"]]},
                          headers=headers["admin"])
    assert preview.status_code == 200 and preview.json()["may_remove_access"]
    blocked = client.patch(f"/api/v1/admin/access/assessment/{identifier}",
                           json={"access_scope": "SELECTED", "assigned_user_ids": [ids["alice"]]},
                           headers=headers["admin"])
    assert blocked.status_code == 409
    changed = client.patch(f"/api/v1/admin/access/assessment/{identifier}",
                           json={"access_scope": "SELECTED", "assigned_user_ids": [ids["alice"]],
                                 "confirm_impact": True}, headers=headers["admin"])
    assert changed.status_code == 200, changed.text
    assert client.get("/api/v1/advanced/assessments", headers=headers["bob"]).json() == []
    assert len(client.get("/api/v1/advanced/assessments", headers=headers["alice"]).json()) == 1


def test_problem_access_scopes_guard_details_catalog_and_judge_without_deleting_progress(access_client):
    client, engine, headers, ids = access_client
    slug = "parity-check"
    assert client.get(f"/api/v1/problems/{slug}").status_code == 200
    changed = client.patch(f"/api/v1/admin/access/problem/{slug}", json={
        "access_scope": "SELECTED", "assigned_user_ids": [ids["alice"]],
        "confirm_impact": True,
    }, headers=headers["admin"])
    assert changed.status_code == 200, changed.text
    assert client.get(f"/api/v1/problems/{slug}").status_code == 404
    assert client.get(f"/api/v1/problems/{slug}", headers=headers["bob"]).status_code == 404
    assert client.get(f"/api/v1/problems/{slug}", headers=headers["alice"]).status_code == 200
    visible = client.get("/api/v1/problems", headers=headers["alice"]).json()["items"]
    hidden = client.get("/api/v1/problems", headers=headers["bob"]).json()["items"]
    assert slug in [item["slug"] for item in visible]
    assert slug not in [item["slug"] for item in hidden]
    payload = {"language": "python", "source_code": "print('Even')", "mode": "SUBMIT"}
    assert client.post(f"/api/v1/problems/{slug}/submissions", json=payload, headers=headers["bob"]).status_code == 404
    submitted = client.post(f"/api/v1/problems/{slug}/submissions", json=payload, headers=headers["alice"])
    assert submitted.status_code == 202, submitted.text
    result_id = submitted.json()["id"]
    returned = client.patch(f"/api/v1/admin/access/problem/{slug}", json={
        "access_scope": "ALL", "assigned_user_ids": [ids["alice"]], "confirm_impact": True,
    }, headers=headers["admin"])
    assert returned.status_code == 200, returned.text
    assert client.get(f"/api/v1/problems/{slug}").status_code == 200
    with Session(engine) as db:
        assert db.get(Submission, result_id) is not None


def test_published_selected_dataset_download_and_practice_are_restricted(access_client):
    client, _, headers, ids = access_client
    source = base64.b64encode(b"region,sales\nNorth,5\nSouth,8\n").decode()
    upload = {
        "title": "Audience sample", "filename": "audience.csv", "content_type": "text/csv",
        "content_base64": source, "publish": True, "access_scope": "SELECTED",
        "assigned_user_ids": [ids["alice"]],
    }
    assert client.post("/api/v1/advanced/datasets", json={**upload, "assigned_user_ids": []},
                       headers=headers["admin"]).status_code == 409
    created = client.post("/api/v1/advanced/datasets", json=upload, headers=headers["admin"])
    assert created.status_code == 201, created.text
    identifier = created.json()["id"]
    library_alice = client.get("/api/v1/advanced/datasets/library", headers=headers["alice"]).json()
    library_bob = client.get("/api/v1/advanced/datasets/library", headers=headers["bob"]).json()
    assert identifier in [item["id"] for item in library_alice]
    assert identifier not in [item["id"] for item in library_bob]
    assert client.get(f"/api/v1/advanced/datasets/{identifier}/download", headers=headers["bob"]).status_code == 404
    assert client.post(f"/api/v1/advanced/datasets/{identifier}/practice",
                       json={"technology": "PANDAS", "source_code": "result = df"},
                       headers=headers["bob"]).status_code == 404
    assert client.get(f"/api/v1/advanced/datasets/{identifier}/download", headers=headers["alice"]).status_code == 200


def test_admin_student_search_does_not_expose_admin_accounts(access_client):
    client, _, headers, ids = access_client
    response = client.get("/api/v1/admin/students", headers=headers["admin"])
    assert response.status_code == 200
    assert {entry["username"] for entry in response.json()} == {"alice", "bob"}
    assert client.get("/api/v1/admin/students", headers=headers["alice"]).status_code == 403
