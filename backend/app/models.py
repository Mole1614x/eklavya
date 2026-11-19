from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint("difficulty IN ('Beginner', 'Easy', 'Medium', 'Hard')", name="problem_difficulty"),
        CheckConstraint(
            "format IN ('CODE', 'EXPRESSION', 'SQL_QUERY', 'NUMERICAL', 'MULTIPLE_CHOICE', 'DATASET_ANALYSIS')",
            name="problem_format",
        ),
    )

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(24), index=True)
    difficulty: Mapped[str] = mapped_column(String(12), index=True)
    format: Mapped[str] = mapped_column(String(24))
    topic: Mapped[str] = mapped_column(String(80), index=True)
    tags: Mapped[list[str]] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text)
    constraints: Mapped[list[str]] = mapped_column(JSON)
    examples: Mapped[list[dict]] = mapped_column(JSON)
    choices: Mapped[list[str]] = mapped_column(JSON)
    starters: Mapped[list["StarterCode"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="StarterCode.language"
    )
    test_cases: Mapped[list["TestCase"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class StarterCode(Base):
    __tablename__ = "starter_code"

    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="CASCADE"), primary_key=True)
    language: Mapped[str] = mapped_column(String(24), primary_key=True)
    code: Mapped[str] = mapped_column(Text)


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="CASCADE"), index=True)
    input_data: Mapped[str] = mapped_column(Text, default="")
    expected_output: Mapped[str] = mapped_column(Text)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    tolerance: Mapped[float | None] = mapped_column(Float, nullable=True)


class ProblemEvaluator(Base):
    __tablename__ = "problem_evaluators"

    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    config: Mapped[dict] = mapped_column(JSON, default=dict)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="learner")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    profile: Mapped["Profile"] = relationship(cascade="all, delete-orphan", lazy="joined")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80))
    bio: Mapped[str] = mapped_column(String(280), default="")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_refresh_token_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccountToken(Base):
    __tablename__ = "account_tokens"
    __table_args__ = (
        CheckConstraint("purpose IN ('verify_email', 'reset_password')", name="account_token_purpose"),
        UniqueConstraint("token_hash", name="uq_account_token_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(24))
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint("mode IN ('RUN', 'SUBMIT')", name="submission_mode"),
        CheckConstraint("status IN ('QUEUED', 'RUNNING', 'FINISHED', 'SYSTEM_ERROR')", name="submission_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="RESTRICT"), index=True)
    language: Mapped[str] = mapped_column(String(24))
    source_code: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), default="QUEUED")
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0)
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RankLevel(Base):
    __tablename__ = "rank_levels"

    slug: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    min_xp: Mapped[int] = mapped_column(Integer, unique=True)
    stars: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, unique=True)


class UserProgress(Base):
    __tablename__ = "user_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    solved_count: Mapped[int] = mapped_column(Integer, default=0)
    current_rank_slug: Mapped[str] = mapped_column(ForeignKey("rank_levels.slug"), default="shishya")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class XPTransaction(Base):
    __tablename__ = "xp_transactions"
    __table_args__ = (UniqueConstraint("user_id", "source_type", "source_id", name="uq_xp_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RankHistory(Base):
    __tablename__ = "rank_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rank_slug: Mapped[str] = mapped_column(ForeignKey("rank_levels.slug"))
    reached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Achievement(Base):
    __tablename__ = "achievements"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(240))
    criteria: Mapped[dict] = mapped_column(JSON)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_slug", name="uq_user_achievement"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_slug: Mapped[str] = mapped_column(ForeignKey("achievements.slug"))
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
