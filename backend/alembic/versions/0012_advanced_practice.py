"""Add timed assessments, practice datasets, and multi-tool progress."""

import sqlalchemy as sa
from alembic import op

revision = "0012_advanced_practice"
down_revision = "0011_performance_reliability"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("instructions", sa.Text, nullable=False, server_default=""),
        sa.Column("assessment_type", sa.String(32), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column("penalty_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("release_results", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("template_key", sa.String(40), nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'UNPUBLISHED', 'ARCHIVED')", name="assessment_status"),
        sa.CheckConstraint("duration_minutes > 0 AND duration_minutes <= 480", name="assessment_duration"),
        sa.CheckConstraint("max_attempts > 0 AND max_attempts <= 20", name="assessment_attempt_limit"),
    )
    op.create_index("ix_assessments_assessment_type", "assessments", ["assessment_type"])
    op.create_index("ix_assessments_opens_at", "assessments", ["opens_at"])
    op.create_index("ix_assessments_closes_at", "assessments", ["closes_at"])
    op.create_index("ix_assessments_status", "assessments", ["status"])
    op.create_index("ix_assessments_created_by", "assessments", ["created_by"])
    op.create_index("ix_assessments_window", "assessments", ["status", "opens_at", "closes_at"])
    op.create_table(
        "assessment_questions",
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="RESTRICT"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("points", sa.Integer, nullable=False, server_default="100"),
        sa.UniqueConstraint("assessment_id", "position", name="uq_assessment_question_position"),
    )
    op.create_table(
        "assessment_assignments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("assessment_id", "user_id", name="uq_assessment_assignment"),
    )
    op.create_index("ix_assessment_assignments_assessment_id", "assessment_assignments", ["assessment_id"])
    op.create_index("ix_assessment_assignments_user_id", "assessment_assignments", ["user_id"])
    op.create_table(
        "learner_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_learner_groups_created_by", "learner_groups", ["created_by"])
    op.create_table(
        "learner_group_members",
        sa.Column("group_id", sa.String(36), sa.ForeignKey("learner_groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "assessment_group_assignments",
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("learner_groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float, nullable=False, server_default="0"),
        sa.Column("max_score", sa.Float, nullable=False, server_default="0"),
        sa.CheckConstraint("status IN ('IN_PROGRESS', 'SUBMITTED', 'EXPIRED')", name="assessment_attempt_status"),
        sa.UniqueConstraint("assessment_id", "user_id", "attempt_number", name="uq_assessment_attempt_number"),
    )
    op.create_index("ix_assessment_attempts_assessment_id", "assessment_attempts", ["assessment_id"])
    op.create_index("ix_assessment_attempts_user_id", "assessment_attempts", ["user_id"])
    op.create_index("ix_assessment_attempts_deadline_at", "assessment_attempts", ["deadline_at"])
    op.create_index("ix_assessment_attempt_deadline", "assessment_attempts", ["status", "deadline_at"])
    op.create_table(
        "assessment_answers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("attempt_id", sa.String(36), sa.ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="RESTRICT"), nullable=False),
        sa.Column("answer", sa.Text, nullable=False, server_default=""),
        sa.Column("language", sa.String(24), nullable=True),
        sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("attempt_id", "problem_slug", name="uq_assessment_answer"),
    )
    op.create_index("ix_assessment_answers_attempt_id", "assessment_answers", ["attempt_id"])
    op.create_index("ix_assessment_answers_problem_slug", "assessment_answers", ["problem_slug"])
    op.create_table(
        "assessment_results",
        sa.Column("attempt_id", sa.String(36), sa.ForeignKey("assessment_attempts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("correct_answers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_answers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("breakdown", sa.JSON, nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "practice_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("category", sa.String(32), nullable=False, server_default="Personal"),
        sa.Column("difficulty", sa.String(12), nullable=False, server_default="Beginner"),
        sa.Column("format", sa.String(12), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="PRIVATE"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("download_allowed", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("column_info", sa.JSON, nullable=False),
        sa.Column("profile", sa.JSON, nullable=False),
        sa.Column("transformations", sa.JSON, nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("format IN ('CSV', 'XLSX', 'JSON', 'PARQUET')", name="practice_dataset_format"),
        sa.CheckConstraint("status IN ('PRIVATE', 'PUBLISHED', 'ARCHIVED')", name="practice_dataset_status"),
    )
    op.create_index("ix_practice_datasets_owner_user_id", "practice_datasets", ["owner_user_id"])
    op.create_index("ix_practice_datasets_category", "practice_datasets", ["category"])
    op.create_index("ix_practice_datasets_status", "practice_datasets", ["status"])
    op.create_index("ix_practice_datasets_created_by", "practice_datasets", ["created_by"])
    op.create_index("ix_practice_datasets_library", "practice_datasets", ["status", "category", "difficulty"])
    op.create_table(
        "dataset_practice_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("practice_datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technology", sa.String(12), nullable=False),
        sa.Column("source_code", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="QUEUED"),
        sa.Column("output", sa.Text, nullable=True),
        sa.Column("execution_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("technology IN ('PANDAS', 'NUMPY', 'SQL')", name="dataset_practice_technology"),
        sa.CheckConstraint("status IN ('QUEUED', 'RUNNING', 'FINISHED', 'SYSTEM_ERROR')", name="dataset_practice_status"),
    )
    op.create_index("ix_dataset_practice_runs_user_id", "dataset_practice_runs", ["user_id"])
    op.create_index("ix_dataset_practice_runs_dataset_id", "dataset_practice_runs", ["dataset_id"])
    op.create_index("ix_dataset_practice_user_created", "dataset_practice_runs", ["user_id", "created_at"])
    op.create_table(
        "multi_tool_progress",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("challenge_key", sa.String(80), nullable=False),
        sa.Column("technology", sa.String(20), nullable=False),
        sa.Column("completed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("score", sa.Float, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "challenge_key", "technology", name="uq_multi_tool_progress"),
    )
    op.create_index("ix_multi_tool_progress_user_id", "multi_tool_progress", ["user_id"])
    op.create_index("ix_multi_tool_progress_challenge_key", "multi_tool_progress", ["challenge_key"])


def downgrade():
    op.drop_table("multi_tool_progress")
    op.drop_table("dataset_practice_runs")
    op.drop_table("practice_datasets")
    op.drop_table("assessment_results")
    op.drop_table("assessment_answers")
    op.drop_table("assessment_attempts")
    op.drop_table("assessment_group_assignments")
    op.drop_table("learner_group_members")
    op.drop_table("learner_groups")
    op.drop_table("assessment_assignments")
    op.drop_table("assessment_questions")
    op.drop_table("assessments")
