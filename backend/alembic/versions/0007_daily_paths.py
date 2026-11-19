"""Add daily challenges and learning paths."""

import sqlalchemy as sa
from alembic import op

revision = "0007_daily_paths"
down_revision = "0006_gamification"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("daily_challenges",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("challenge_date", sa.Date, nullable=False),
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="RESTRICT"), nullable=False),
        sa.Column("xp_reward", sa.Integer, nullable=False, server_default="20"))
    op.create_index("ix_daily_challenges_challenge_date", "daily_challenges", ["challenge_date"], unique=True)
    op.create_table("daily_challenge_completions",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("daily_challenge_id", sa.Integer, sa.ForeignKey("daily_challenges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "daily_challenge_id", name="uq_daily_completion"))
    op.create_index("ix_daily_challenge_completions_user_id", "daily_challenge_completions", ["user_id"])
    op.create_table("learning_paths",
        sa.Column("slug", sa.String(64), primary_key=True), sa.Column("title", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=False), sa.Column("prerequisites", sa.JSON, nullable=False))
    op.create_table("learning_path_problems",
        sa.Column("path_slug", sa.String(64), sa.ForeignKey("learning_paths.slug", ondelete="CASCADE"), primary_key=True),
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False), sa.Column("milestone", sa.String(120)))
    op.create_table("learning_path_progress",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path_slug", sa.String(64), sa.ForeignKey("learning_paths.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "path_slug", name="uq_learning_path_progress"))
    op.create_index("ix_learning_path_progress_user_id", "learning_path_progress", ["user_id"])


def downgrade():
    op.drop_table("learning_path_progress")
    op.drop_table("learning_path_problems")
    op.drop_table("learning_paths")
    op.drop_table("daily_challenge_completions")
    op.drop_table("daily_challenges")
