from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.judge_client import get_enqueuer
from app.main import app
from app.main_dependencies import get_db
from app.models import (
    Contest, ContestRating, ContestRegistration, ContestSubmission, Submission, User, UserAchievement,
)
from app.seed import seed


@pytest.fixture
def contest_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'contests.db'}")
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
                    "email": f"archer{index}@example.com", "username": f"archer{index}",
                    "password": "StrongPass123", "display_name": f"Archer {index}",
                })
                tokens.append({"Authorization": f"Bearer {response.json()['access_token']}"})
            yield client, engine, tokens
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_registration_is_idempotent_and_problems_unlock_at_start(contest_client):
    client, engine, headers = contest_client
    contest = client.get("/api/v1/contests").json()[0]
    slug = contest["slug"]
    detail = client.get(f"/api/v1/contests/{slug}").json()
    assert detail["status"] == "UPCOMING"
    assert detail["problems"] == []
    assert client.post(f"/api/v1/contests/{slug}/register", headers=headers[0]).status_code == 204
    assert client.post(f"/api/v1/contests/{slug}/register", headers=headers[0]).status_code == 204
    with Session(engine) as db:
        assert db.scalar(select(func.count(ContestRegistration.id))) == 1
        item = db.scalar(select(Contest).where(Contest.slug == slug))
        item.starts_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        item.ends_at = datetime.now(timezone.utc) + timedelta(minutes=85)
        db.commit()
    assert len(client.get(f"/api/v1/contests/{slug}").json()["problems"]) == 3
    assert client.post(
        f"/api/v1/contests/{slug}/problems/pair-indices/submissions", headers=headers[1],
        json={"language": "python", "source_code": "print('x')"},
    ).status_code == 403


def test_contest_submission_is_tracked_and_awards_first_contest(contest_client):
    client, engine, headers = contest_client
    slug = client.get("/api/v1/contests").json()[0]["slug"]
    with Session(engine) as db:
        contest = db.scalar(select(Contest).where(Contest.slug == slug))
        user = db.scalar(select(User).where(User.username == "archer1"))
        contest.starts_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        contest.ends_at = datetime.now(timezone.utc) + timedelta(minutes=85)
        db.add(ContestRegistration(contest_id=contest.id, user_id=user.id))
        db.commit()
    response = client.post(
        f"/api/v1/contests/{slug}/problems/pair-indices/submissions", headers=headers[0],
        json={"language": "python", "source_code": "print('x')", "mode": "RUN"},
    )
    assert response.status_code == 202
    with Session(engine) as db:
        submission = db.get(Submission, response.json()["id"])
        assert submission.mode == "SUBMIT"
        assert submission.contest_id is not None
        assert db.scalar(select(func.count(ContestSubmission.id))) == 1
        assert db.scalar(select(UserAchievement).where(
            UserAchievement.user_id == submission.user_id,
            UserAchievement.achievement_slug == "first-contest",
        )) is not None


def test_leaderboard_penalty_ratings_and_history(contest_client):
    client, engine, headers = contest_client
    slug = client.get("/api/v1/contests").json()[0]["slug"]
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    with Session(engine) as db:
        contest = db.scalar(select(Contest).where(Contest.slug == slug))
        contest.starts_at = start
        contest.ends_at = datetime.now(timezone.utc) + timedelta(hours=1)
        users = list(db.scalars(select(User).order_by(User.username)))
        for user in users:
            db.add(ContestRegistration(contest_id=contest.id, user_id=user.id))
        db.flush()
        attempts = [
            ("wrong", users[0], "WRONG_ANSWER", 300),
            ("accepted-1", users[0], "ACCEPTED", 600),
            ("accepted-2", users[1], "ACCEPTED", 1200),
        ]
        for submission_id, user, verdict, seconds in attempts:
            submission = Submission(
                id=submission_id, user_id=user.id, contest_id=contest.id, problem_slug="pair-indices",
                language="python", source_code="pass", mode="SUBMIT", status="FINISHED", verdict=verdict,
            )
            db.add(submission)
            db.flush()
            db.add(ContestSubmission(
                contest_id=contest.id, user_id=user.id, problem_slug="pair-indices",
                submission_id=submission.id, submitted_at=start + timedelta(seconds=seconds),
            ))
        db.commit()
    board = client.get(f"/api/v1/contests/{slug}/leaderboard").json()
    assert [row["username"] for row in board] == ["archer2", "archer1"]
    assert board[1]["penalty_seconds"] == 1800
    with Session(engine) as db:
        contest = db.scalar(select(Contest).where(Contest.slug == slug))
        contest.ends_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        admin = db.scalar(select(User).where(User.username == "archer1"))
        admin.role = "admin"
        db.commit()
    assert client.post(f"/api/v1/contests/{slug}/finalize", headers=headers[0]).status_code == 204
    assert client.post(f"/api/v1/contests/{slug}/finalize", headers=headers[0]).status_code == 204
    with Session(engine) as db:
        ratings = list(db.scalars(select(ContestRating).order_by(ContestRating.position)))
        assert len(ratings) == 2
        assert [(item.position, item.rating_after) for item in ratings] == [(1, 1216), (2, 1184)]
    history = client.get("/api/v1/contests/me/history", headers=headers[0]).json()
    assert history[0]["slug"] == slug
    assert history[0]["delta"] == -16
