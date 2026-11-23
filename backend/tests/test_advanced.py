import base64
import io
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.dataset_lab import DatasetError, validate_xlsx_archive
from app.database import Base
from app.main import app
from app.main_dependencies import get_db
from app.judge_client import get_dataset_practice_enqueuer, get_enqueuer
from app.models import AssessmentAttempt, DatasetPracticeRun, PracticeDataset, Submission, User
from app.seed import seed


@pytest.fixture
def advanced_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'advanced.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db: seed(db)

    def override():
        with Session(engine) as db: yield db

    original_storage, original_limit = settings().dataset_storage_dir, settings().dataset_max_bytes
    settings().dataset_storage_dir, settings().dataset_max_bytes = tmp_path / "datasets", 50_000
    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_enqueuer] = lambda: lambda submission_id: None
    app.dependency_overrides[get_dataset_practice_enqueuer] = lambda: lambda run_id: None
    try:
        with TestClient(app) as client:
            tokens = {}
            for name in ("admin", "learner", "other"):
                response = client.post("/api/v1/auth/register", json={
                    "email": f"{name}@example.com", "username": name,
                    "password": "StrongPass123", "display_name": name.title(),
                })
                tokens[name] = response.json()["access_token"]
            with Session(engine) as db:
                db.scalar(select(User).where(User.username == "admin")).role = "admin"; db.commit()
                ids = {user.username: user.id for user in db.scalars(select(User))}
            yield client, engine, {name: {"Authorization": f"Bearer {token}"} for name, token in tokens.items()}, ids, tmp_path
    finally:
        settings().dataset_storage_dir, settings().dataset_max_bytes = original_storage, original_limit
        app.dependency_overrides.clear(); engine.dispose()


def assessment_payload(learner_id: int):
    now = datetime.now(timezone.utc)
    return {
        "title": "Timed Foundations", "description": "Server-timed assessment", "instructions": "Answer every question.",
        "assessment_type": "CODING", "duration_minutes": 30,
        "opens_at": (now - timedelta(minutes=1)).isoformat(), "closes_at": (now + timedelta(hours=1)).isoformat(),
        "max_attempts": 1, "penalty_percent": 0, "release_results": True, "status": "PUBLISHED",
        "questions": [{"problem_slug": "parity-check", "points": 100}], "assigned_user_ids": [learner_id],
    }


def test_xlsx_archive_expansion_is_bounded():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", "x" * 100)
    with pytest.raises(DatasetError, match="decompressed-size"):
        validate_xlsx_archive(output.getvalue(), max_uncompressed_bytes=10)


def test_assessment_rbac_timer_autosave_and_idempotent_finalization(advanced_client):
    client, engine, headers, ids, _ = advanced_client
    assert client.post("/api/v1/advanced/admin/assessments", headers=headers["learner"], json=assessment_payload(ids["learner"])).status_code == 403
    created = client.post("/api/v1/advanced/admin/assessments", headers=headers["admin"], json=assessment_payload(ids["learner"]))
    assert created.status_code == 201
    assessment_id = created.json()["id"]
    assert len(client.get("/api/v1/advanced/assessments", headers=headers["learner"]).json()) == 1
    assert client.get("/api/v1/advanced/assessments", headers=headers["other"]).json() == []

    attempt = client.post(f"/api/v1/advanced/assessments/{assessment_id}/start", headers=headers["learner"]).json()
    resumed = client.post(f"/api/v1/advanced/assessments/{assessment_id}/start", headers=headers["learner"]).json()
    assert resumed["id"] == attempt["id"]
    saved = client.put(f"/api/v1/advanced/assessments/attempts/{attempt['id']}/answers", headers=headers["learner"], json={
        "problem_slug": "parity-check", "answer": "Odd",
    })
    assert saved.status_code == 200 and saved.json()["answers"][0]["answer"] == "Odd"
    first = client.post(f"/api/v1/advanced/assessments/attempts/{attempt['id']}/submit", headers=headers["learner"])
    second = client.post(f"/api/v1/advanced/assessments/attempts/{attempt['id']}/submit", headers=headers["learner"])
    assert first.json()["status"] == second.json()["status"] == "SUBMITTED"
    assert first.json()["score"] == 100
    assert client.post(f"/api/v1/advanced/assessments/{assessment_id}/start", headers=headers["learner"]).status_code == 409

    export = client.get(f"/api/v1/advanced/admin/assessments/{assessment_id}/export?format=csv", headers=headers["admin"])
    assert export.status_code == 200 and b"learner" in export.content
    with Session(engine) as db: assert db.get(AssessmentAttempt, attempt["id"]).finalized_at is not None


def test_group_assignment_and_secure_assessment_judge_submission(advanced_client):
    client, engine, headers, ids, _ = advanced_client
    group = client.post("/api/v1/advanced/admin/groups", headers=headers["admin"], json={
        "name": "Cohort A", "user_ids": [ids["learner"]],
    })
    assert group.status_code == 201
    payload = assessment_payload(ids["learner"])
    payload["assigned_user_ids"] = []
    payload["assigned_group_ids"] = [group.json()["id"]]
    assessment_id = client.post("/api/v1/advanced/admin/assessments", headers=headers["admin"], json=payload).json()["id"]
    assert len(client.get("/api/v1/advanced/assessments", headers=headers["learner"]).json()) == 1
    attempt = client.post(f"/api/v1/advanced/assessments/{assessment_id}/start", headers=headers["learner"]).json()
    submitted = client.post(f"/api/v1/advanced/assessments/attempts/{attempt['id']}/questions/parity-check/submissions", headers=headers["learner"], json={
        "language": "python", "source_code": "n = int(input())\nprint('Even' if n % 2 == 0 else 'Odd')", "mode": "SUBMIT",
    })
    assert submitted.status_code == 202
    with Session(engine) as db:
        item = db.get(Submission, submitted.json()["id"]); item.status = "FINISHED"; item.verdict = "ACCEPTED"; db.commit()
    finalized = client.post(f"/api/v1/advanced/assessments/attempts/{attempt['id']}/submit", headers=headers["learner"])
    assert finalized.json()["score"] == 100


def test_expired_attempt_is_finalized_on_autosave(advanced_client):
    client, engine, headers, ids, _ = advanced_client
    assessment_id = client.post("/api/v1/advanced/admin/assessments", headers=headers["admin"], json=assessment_payload(ids["learner"])).json()["id"]
    attempt = client.post(f"/api/v1/advanced/assessments/{assessment_id}/start", headers=headers["learner"]).json()
    with Session(engine) as db:
        item = db.get(AssessmentAttempt, attempt["id"]); item.deadline_at = datetime.now(timezone.utc) - timedelta(seconds=1); db.commit()
    response = client.put(f"/api/v1/advanced/assessments/attempts/{attempt['id']}/answers", headers=headers["learner"], json={"problem_slug": "parity-check", "answer": "Odd"})
    assert response.status_code == 409
    with Session(engine) as db: assert db.get(AssessmentAttempt, attempt["id"]).status == "EXPIRED"


def test_private_dataset_profile_transform_download_and_isolation(advanced_client):
    client, engine, headers, _, _ = advanced_client
    content = b"name,score,note\nAnu,10,ok\nAnu,10,ok\nDev,,=HYPERLINK(1)\n"
    payload = {"title": "Scores", "filename": "scores.csv", "content_type": "text/csv", "content_base64": base64.b64encode(content).decode()}
    created = client.post("/api/v1/advanced/datasets", headers=headers["learner"], json=payload)
    assert created.status_code == 201
    dataset_id = created.json()["id"]
    assert created.json()["profile"]["duplicate_rows"] == 1
    assert client.get(f"/api/v1/advanced/datasets/{dataset_id}/download", headers=headers["other"]).status_code == 404
    transformed = client.post(f"/api/v1/advanced/datasets/{dataset_id}/transform", headers=headers["learner"], json={"operation": "drop_duplicates"})
    assert transformed.json()["profile"]["rows"] == 2
    download = client.get(f"/api/v1/advanced/datasets/{dataset_id}/download", headers=headers["learner"])
    assert b"'=HYPERLINK" in download.content
    invalid = client.post("/api/v1/advanced/datasets", headers=headers["learner"], json={**payload, "filename": "../scores.csv"})
    assert invalid.status_code == 422
    run = client.post(f"/api/v1/advanced/datasets/{dataset_id}/practice", headers=headers["learner"], json={
        "technology": "PANDAS", "source_code": "result = df.drop_duplicates()",
    })
    assert run.status_code == 202 and run.json()["status"] == "QUEUED"
    assert client.get(f"/api/v1/advanced/datasets/practice/{run.json()['id']}", headers=headers["other"]).status_code == 404
    assert client.delete(f"/api/v1/advanced/datasets/{dataset_id}", headers=headers["learner"]).status_code == 204
    with Session(engine) as db:
        assert db.get(PracticeDataset, dataset_id).status == "ARCHIVED"
        assert db.get(DatasetPracticeRun, run.json()["id"]) is not None


def test_safe_excel_tableau_and_multi_tool_graders(advanced_client):
    client, _, headers, _, _ = advanced_client
    excel = client.post("/api/v1/advanced/excel/evaluate", headers=headers["learner"], json={
        "expression": "=SUMIF(A2:A4,E2,B2:B4)", "cells": {"A2": "West", "A3": "East", "A4": "West", "B2": 5, "B3": 8, "B4": 7, "E2": "West"}, "expected": 12,
    }).json()
    assert excel["valid"] and excel["passed"] and excel["result"] == 12
    malicious = client.post("/api/v1/advanced/excel/evaluate", headers=headers["learner"], json={"expression": "=__import__(\"os\")"}).json()
    assert malicious["valid"] is False
    tableau = client.post("/api/v1/advanced/tableau/evaluate", headers=headers["learner"], json={
        "expression": "{ FIXED [Region] : SUM([Sales]) }", "rows": [{"Region": "West", "Sales": 5}, {"Region": "West", "Sales": 7}], "expected": {"West": 12},
    }).json()
    assert tableau["valid"] and tableau["passed"]
    multi = client.post("/api/v1/advanced/multi-tool/submit", headers=headers["learner"], json={
        "challenge_key": "sales-by-region", "technology": "SQL", "answer": "SELECT Region, SUM(Sales) FROM Orders GROUP BY Region",
    }).json()
    assert multi["passed"] is True
