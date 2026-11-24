import base64
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.main import app
from app.main_dependencies import get_db
from app.judge_client import get_enqueuer
from app.models import AuditLog, Contest, ContestRating, ManagedDataset, Submission, User
from app.seed import seed


@pytest.fixture
def admin_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'admin.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)

    def override():
        with Session(engine) as db:
            yield db

    original_storage = settings().dataset_storage_dir
    original_limit = settings().dataset_max_bytes
    settings().dataset_storage_dir = tmp_path / "private-datasets"
    settings().dataset_max_bytes = 2048
    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_enqueuer] = lambda: lambda submission_id: None
    try:
        with TestClient(app) as client:
            tokens = {}
            for role in ("admin", "learner"):
                response = client.post("/api/v1/auth/register", json={
                    "email": f"{role}@example.com", "username": role,
                    "password": "StrongPass123", "display_name": role.title(),
                })
                tokens[role] = response.json()["access_token"]
            with Session(engine) as db:
                db.scalar(select(User).where(User.username == "admin")).role = "admin"
                db.commit()
            yield client, engine, {
                role: {"Authorization": f"Bearer {token}"} for role, token in tokens.items()
            }, tmp_path
    finally:
        settings().dataset_storage_dir = original_storage
        settings().dataset_max_bytes = original_limit
        app.dependency_overrides.clear()
        engine.dispose()


def problem_payload(problem_status="DRAFT"):
    return {
        "title": "Admin Managed Sum", "category": "foundations", "difficulty": "Beginner",
        "format": "CODE", "topic": "Administration", "tags": ["admin"],
        "description": "Read two integers and print their sum.", "constraints": ["Integers only"],
        "examples": [{"input": "1 2\n", "output": "3\n"}], "choices": [],
        "status": problem_status,
        "starters": [{"language": "python", "code": "a, b = map(int, input().split())\n"}],
        "test_cases": [{
            "input_data": "1 2\n", "expected_output": "3\n", "is_hidden": False, "position": 0,
        }, {
            "input_data": "-1 4\n", "expected_output": "3\n", "is_hidden": True, "position": 1,
        }],
        "evaluator": None,
    }


def test_admin_rbac_problem_lifecycle_and_audit(admin_client):
    client, engine, headers, _ = admin_client
    assert client.get("/api/v1/admin/overview", headers=headers["learner"]).status_code == 403
    assert client.get("/api/v1/admin/overview", headers=headers["admin"]).status_code == 200

    created = client.put(
        "/api/v1/admin/problems/admin-managed-sum", headers=headers["admin"], json=problem_payload(),
    )
    assert created.status_code == 200
    assert created.json()["hidden_test_count"] == 1
    assert client.get("/api/v1/problems/admin-managed-sum").status_code == 404

    published = client.patch(
        "/api/v1/admin/problems/admin-managed-sum/status", headers=headers["admin"],
        json={"status": "PUBLISHED", "reason": "Reviewed hidden and public tests"},
    )
    assert published.status_code == 200
    assert client.get("/api/v1/problems/admin-managed-sum").status_code == 200
    archived = client.patch(
        "/api/v1/admin/problems/admin-managed-sum/status", headers=headers["admin"],
        json={"status": "ARCHIVED", "reason": "Retired from the public catalog"},
    )
    assert archived.status_code == 200
    assert client.get("/api/v1/problems/admin-managed-sum").status_code == 404
    with Session(engine) as db:
        assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.target_id == "admin-managed-sum")) == 3


def test_private_dataset_validation_versioning_and_status(admin_client):
    client, engine, headers, _ = admin_client
    encoded = base64.b64encode(b"name,score\nAnu,10\nDev,12\n").decode()
    payload = {
        "name": "student-scores", "kind": "PANDAS", "filename": "scores.csv",
        "content_type": "text/csv", "content_base64": encoded,
    }
    first = client.post("/api/v1/admin/datasets", headers=headers["admin"], json=payload)
    second = client.post("/api/v1/admin/datasets", headers=headers["admin"], json=payload)
    assert (first.status_code, second.status_code) == (201, 201)
    assert [first.json()["version"], second.json()["version"]] == [1, 2]
    assert client.get("/api/v1/admin/datasets", headers=headers["learner"]).status_code == 403
    download = client.get(
        f"/api/v1/admin/datasets/{first.json()['id']}/download", headers=headers["admin"],
    )
    assert download.content == base64.b64decode(encoded)
    disabled = client.patch(
        f"/api/v1/admin/datasets/{first.json()['id']}", headers=headers["admin"],
        json={"is_active": False, "reason": "Superseded by version two"},
    )
    assert disabled.json()["is_active"] is False
    invalid = client.post("/api/v1/admin/datasets", headers=headers["admin"], json={
        **payload, "filename": "../secret.csv",
    })
    assert invalid.status_code == 422
    spoofed = client.post("/api/v1/admin/datasets", headers=headers["admin"], json={
        **payload, "filename": "scores.json", "content_type": "application/json",
    })
    assert spoofed.status_code == 422
    oversized = client.post("/api/v1/admin/datasets", headers=headers["admin"], json={
        **payload, "content_base64": base64.b64encode(b"x" * 2049).decode(),
    })
    assert oversized.status_code == 413
    with Session(engine) as db:
        stored = db.get(ManagedDataset, first.json()["id"])
        assert stored.storage_path.endswith(".csv")


def test_user_suspension_invalidates_existing_access_and_prevents_self_lockout(admin_client):
    client, _, headers, _ = admin_client
    users = client.get("/api/v1/admin/users", headers=headers["admin"]).json()
    learner = next(user for user in users if user["username"] == "learner")
    admin = next(user for user in users if user["username"] == "admin")
    suspended = client.patch(
        f"/api/v1/admin/users/{learner['id']}/status", headers=headers["admin"],
        json={"is_active": False, "reason": "Confirmed policy violation"},
    )
    assert suspended.json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=headers["learner"]).status_code == 401
    assert client.patch(
        f"/api/v1/admin/users/{admin['id']}/status", headers=headers["admin"],
        json={"is_active": False, "reason": "Would remove the active administrator"},
    ).status_code == 409


def test_contest_path_achievement_and_finalized_result_controls(admin_client):
    client, engine, headers, _ = admin_client
    now = datetime.now(timezone.utc)
    contest_payload = {
        "title": "Admin Arena", "description": "Managed contest",
        "starts_at": (now + timedelta(days=1)).isoformat(),
        "ends_at": (now + timedelta(days=1, hours=1)).isoformat(),
        "is_rated": True, "publication_status": "DRAFT",
        "problems": [{"problem_slug": "parity-check", "points": 100}],
    }
    contest = client.put(
        "/api/v1/admin/contests/admin-arena", headers=headers["admin"], json=contest_payload,
    )
    assert contest.status_code == 200
    assert contest.json()["problem_count"] == 1
    assert client.patch(
        "/api/v1/admin/contests/admin-arena/status", headers=headers["admin"],
        json={"status": "PUBLISHED", "reason": "Schedule and problems reviewed"},
    ).status_code == 200
    assert client.get(
        "/api/v1/admin/contests/admin-arena/registrations", headers=headers["admin"],
    ).json() == []
    assert client.get(
        "/api/v1/admin/contests/admin-arena/standings", headers=headers["admin"],
    ).json() == []
    assert client.get(
        "/api/v1/admin/contests/admin-arena/submissions", headers=headers["admin"],
    ).json() == []

    path_payload = {
        "title": "Admin Foundations", "description": "A managed learning path",
        "prerequisites": [], "status": "PUBLISHED",
        "problems": [{"problem_slug": "parity-check", "milestone": "First verified solve"}],
    }
    path = client.put(
        "/api/v1/admin/paths/admin-foundations", headers=headers["admin"], json=path_payload,
    )
    assert path.status_code == 200
    assert path.json()["problem_count"] == 1
    assert any(item["slug"] == "admin-foundations" for item in client.get("/api/v1/learning/paths").json())

    achievement = client.put(
        "/api/v1/admin/achievements/admin-first-solve", headers=headers["admin"], json={
            "name": "Admin First Solve", "description": "Complete one verified problem",
            "criteria": {"solved": 1}, "xp_reward": 5,
        },
    )
    assert achievement.status_code == 200
    assert achievement.json()["xp_reward"] == 5
    assert client.get("/api/v1/admin/xp-transactions", headers=headers["admin"]).status_code == 200

    with Session(engine) as db:
        stored_contest = db.scalar(select(Contest).where(Contest.slug == "admin-arena"))
        learner = db.scalar(select(User).where(User.username == "learner"))
        db.add(ContestRating(
            contest_id=stored_contest.id, user_id=learner.id,
            rating_before=1200, rating_after=1200, position=1,
        ))
        db.commit()
    assert client.put(
        "/api/v1/admin/contests/admin-arena", headers=headers["admin"], json=contest_payload,
    ).status_code == 409
    logs = client.get("/api/v1/admin/audit-logs", headers=headers["admin"]).json()
    assert {item["target_type"] for item in logs} >= {"contest", "learning_path", "achievement"}


def test_stuck_judge_recovery_is_audited_and_idempotent(admin_client):
    client, engine, headers, _ = admin_client
    with Session(engine) as db:
        admin = db.scalar(select(User).where(User.username == "admin"))
        db.add(Submission(
            id="stuck-admin-recovery", user_id=admin.id, problem_slug="parity-check",
            language="python", source_code="print('Even')", mode="SUBMIT",
            status="RUNNING", attempt_count=1,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        ))
        db.commit()
    recovered = client.post("/api/v1/admin/judge/recover-stuck", headers=headers["admin"], json={})
    assert recovered.status_code == 200
    assert recovered.json() == {"recovered": 1, "cancelled": 0, "failed_to_enqueue": 0}
    assert client.post(
        "/api/v1/admin/judge/recover-stuck", headers=headers["admin"], json={},
    ).json()["recovered"] == 0
    with Session(engine) as db:
        assert db.get(Submission, "stuck-admin-recovery").status == "QUEUED"
        assert db.scalar(select(AuditLog.id).where(AuditLog.action == "judge.recover_stuck")) is not None


def test_duplicate_detection_reuses_existing_problem_instead_of_creating_copy(admin_client):
    client, engine, headers, _ = admin_client
    original = problem_payload()
    first = client.put("/api/v1/admin/problems/admin-managed-sum",
                       headers=headers["admin"], json=original)
    assert first.status_code == 200, first.text

    candidate = {**original, "title": "Admin: managed SUM!"}
    duplicate = client.put("/api/v1/admin/problems/admin-managed-sum-copy",
                           headers=headers["admin"], json=candidate)
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["detail"]["existing_slug"] == "admin-managed-sum"
    assert client.get("/api/v1/admin/problems/admin-managed-sum-copy",
                      headers=headers["admin"]).status_code == 404

    check = client.get("/api/v1/admin/problems/duplicate-check",
                       params={"title": "Admin managed sum", "category": "foundations",
                               "topic": "Administration", "format": "CODE"},
                       headers=headers["admin"])
    assert check.status_code == 200, check.text
    assert check.json()["duplicates"][0]["slug"] == "admin-managed-sum"

    forbidden = client.get("/api/v1/admin/problems/duplicate-check",
                           params={"title": "Admin managed sum", "category": "foundations",
                                   "format": "CODE"}, headers=headers["learner"])
    assert forbidden.status_code == 403

    edited = client.put("/api/v1/admin/problems/admin-managed-sum",
                        headers=headers["admin"], json=original | {
                            "description": "Read two integers and print their exact arithmetic sum."
                        })
    assert edited.status_code == 200, edited.text

    distinct = client.put("/api/v1/admin/problems/unique-even-sum",
                          headers=headers["admin"], json=original | {
                              "title": "Sum of Positive Even Numbers",
                              "description": "Read N and sum strictly positive even integers up to N.",
                          })
    assert distinct.status_code == 200, distinct.text
