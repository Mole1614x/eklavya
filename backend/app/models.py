from datetime import date, datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint("difficulty IN ('Beginner', 'Easy', 'Medium', 'Hard')", name="problem_difficulty"),
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'UNPUBLISHED', 'ARCHIVED')", name="problem_status"),
        CheckConstraint(
            "format IN ('CODE', 'EXPRESSION', 'SQL_QUERY', 'NUMERICAL', 'MULTIPLE_CHOICE', 'DATASET_ANALYSIS')",
            name="problem_format",
        ),
        Index("ix_problems_catalog", "status", "category", "difficulty", "topic", "title"),
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
    status: Mapped[str] = mapped_column(String(16), default="PUBLISHED", index=True)
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
    __table_args__ = (Index("ix_users_active_created", "is_active", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="learner")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'FINISHED', 'SYSTEM_ERROR', 'CANCELLED')",
            name="submission_status",
        ),
        Index("ix_submissions_user_created_at", "user_id", "created_at", "id"),
        Index("ix_submissions_status_created_at", "status", "created_at"),
        Index("ix_submissions_problem_verdict", "problem_slug", "verdict"),
        Index("ix_submissions_user_status_created", "user_id", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="RESTRICT"), index=True)
    contest_id: Mapped[int | None] = mapped_column(ForeignKey("contests.id", ondelete="RESTRICT", name="fk_submissions_contest_id"), nullable=True, index=True)
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
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    __table_args__ = (Index("ix_user_progress_leaderboard", "xp", "updated_at"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    solved_count: Mapped[int] = mapped_column(Integer, default=0)
    current_rank_slug: Mapped[str] = mapped_column(ForeignKey("rank_levels.slug"), default="shishya")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class XPTransaction(Base):
    __tablename__ = "xp_transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "source_type", "source_id", name="uq_xp_source"),
        Index("ix_xp_transactions_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RankHistory(Base):
    __tablename__ = "rank_history"
    __table_args__ = (Index("ix_rank_history_user_reached", "user_id", "reached_at"),)

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


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="RESTRICT"))
    xp_reward: Mapped[int] = mapped_column(Integer, default=20)


class DailyChallengeCompletion(Base):
    __tablename__ = "daily_challenge_completions"
    __table_args__ = (UniqueConstraint("user_id", "daily_challenge_id", name="uq_daily_completion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    daily_challenge_id: Mapped[int] = mapped_column(ForeignKey("daily_challenges.id", ondelete="CASCADE"))
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="RESTRICT"), unique=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LearningPath(Base):
    __tablename__ = "learning_paths"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')", name="learning_path_status"),
    )

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(String(500))
    prerequisites: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="PUBLISHED", index=True)


class LearningPathProblem(Base):
    __tablename__ = "learning_path_problems"

    path_slug: Mapped[str] = mapped_column(ForeignKey("learning_paths.slug", ondelete="CASCADE"), primary_key=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    milestone: Mapped[str | None] = mapped_column(String(120), nullable=True)


class LearningPathProgress(Base):
    __tablename__ = "learning_path_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "path_slug", name="uq_learning_path_progress"),
        Index("ix_learning_path_progress_path", "path_slug", "enrolled_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    path_slug: Mapped[str] = mapped_column(ForeignKey("learning_paths.slug", ondelete="CASCADE"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Contest(Base):
    __tablename__ = "contests"
    __table_args__ = (
        CheckConstraint(
            "publication_status IN ('DRAFT', 'PUBLISHED', 'CANCELLED', 'FINALIZED')",
            name="contest_publication_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(500), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_rated: Mapped[bool] = mapped_column(Boolean, default=True)
    publication_status: Mapped[str] = mapped_column(String(16), default="PUBLISHED", index=True)


class ContestProblem(Base):
    __tablename__ = "contest_problems"

    contest_id: Mapped[int] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="RESTRICT"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer, default=100)


class ContestRegistration(Base):
    __tablename__ = "contest_registrations"
    __table_args__ = (UniqueConstraint("contest_id", "user_id", name="uq_contest_registration"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContestSubmission(Base):
    __tablename__ = "contest_submissions"
    __table_args__ = (
        Index("ix_contest_submissions_standings", "contest_id", "user_id", "problem_slug", "submitted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="RESTRICT"))
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), unique=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContestRating(Base):
    __tablename__ = "contest_ratings"
    __table_args__ = (UniqueConstraint("contest_id", "user_id", name="uq_contest_rating"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rating_before: Mapped[int] = mapped_column(Integer)
    rating_after: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)


class ManagedDataset(Base):
    __tablename__ = "managed_datasets"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('SQL', 'PANDAS', 'NUMPY', 'STATISTICS', 'PYSPARK', 'MACHINE_LEARNING')",
            name="managed_dataset_kind",
        ),
        UniqueConstraint("name", "version", name="uq_managed_dataset_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str] = mapped_column(String(120))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'UNPUBLISHED', 'ARCHIVED')", name="assessment_status"),
        CheckConstraint("duration_minutes > 0 AND duration_minutes <= 480", name="assessment_duration"),
        CheckConstraint("max_attempts > 0 AND max_attempts <= 20", name="assessment_attempt_limit"),
        Index("ix_assessments_window", "status", "opens_at", "closes_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(1000), default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    assessment_type: Mapped[str] = mapped_column(String(32), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    penalty_percent: Mapped[float] = mapped_column(Float, default=0)
    release_results: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    template_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    __table_args__ = (UniqueConstraint("assessment_id", "position", name="uq_assessment_question_position"),)

    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="RESTRICT"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer, default=100)


class AssessmentAssignment(Base):
    __tablename__ = "assessment_assignments"
    __table_args__ = (UniqueConstraint("assessment_id", "user_id", name="uq_assessment_assignment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LearnerGroup(Base):
    __tablename__ = "learner_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LearnerGroupMember(Base):
    __tablename__ = "learner_group_members"

    group_id: Mapped[str] = mapped_column(ForeignKey("learner_groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssessmentGroupAssignment(Base):
    __tablename__ = "assessment_group_assignments"

    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("learner_groups.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (
        UniqueConstraint("assessment_id", "user_id", "attempt_number", name="uq_assessment_attempt_number"),
        CheckConstraint("status IN ('IN_PROGRESS', 'SUBMITTED', 'EXPIRED')", name="assessment_attempt_status"),
        Index("ix_assessment_attempt_deadline", "status", "deadline_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="IN_PROGRESS")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    max_score: Mapped[float] = mapped_column(Float, default=0)


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "problem_slug", name="uq_assessment_answer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("assessment_attempts.id", ondelete="CASCADE"), index=True)
    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="RESTRICT"), index=True)
    answer: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str | None] = mapped_column(String(24), nullable=True)
    submission_id: Mapped[str | None] = mapped_column(ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    attempt_id: Mapped[str] = mapped_column(ForeignKey("assessment_attempts.id", ondelete="CASCADE"), primary_key=True)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    total_answers: Mapped[int] = mapped_column(Integer, default=0)
    breakdown: Mapped[list[dict]] = mapped_column(JSON, default=list)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PracticeDataset(Base):
    __tablename__ = "practice_datasets"
    __table_args__ = (
        CheckConstraint("format IN ('CSV', 'XLSX', 'JSON', 'PARQUET')", name="practice_dataset_format"),
        CheckConstraint("status IN ('PRIVATE', 'PUBLISHED', 'ARCHIVED')", name="practice_dataset_status"),
        Index("ix_practice_datasets_library", "status", "category", "difficulty"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(1000), default="")
    category: Mapped[str] = mapped_column(String(32), default="Personal", index=True)
    difficulty: Mapped[str] = mapped_column(String(12), default="Beginner")
    format: Mapped[str] = mapped_column(String(12))
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="PRIVATE", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    download_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    column_info: Mapped[list[dict]] = mapped_column(JSON, default=list)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    transformations: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MultiToolProgress(Base):
    __tablename__ = "multi_tool_progress"
    __table_args__ = (UniqueConstraint("user_id", "challenge_key", "technology", name="uq_multi_tool_progress"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_key: Mapped[str] = mapped_column(String(80), index=True)
    technology: Mapped[str] = mapped_column(String(20))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DatasetPracticeRun(Base):
    __tablename__ = "dataset_practice_runs"
    __table_args__ = (
        CheckConstraint("technology IN ('PANDAS', 'NUMPY', 'SQL')", name="dataset_practice_technology"),
        CheckConstraint("status IN ('QUEUED', 'RUNNING', 'FINISHED', 'SYSTEM_ERROR')", name="dataset_practice_status"),
        Index("ix_dataset_practice_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("practice_datasets.id", ondelete="CASCADE"), index=True)
    technology: Mapped[str] = mapped_column(String(12))
    source_code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="QUEUED")
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
