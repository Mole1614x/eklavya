"""Add performance indexes and reliable submission cancellation metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0011_performance_reliability"
down_revision = "0010_admin_console"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("submission_status", "submissions", type_="check")
    op.create_check_constraint(
        "submission_status", "submissions",
        "status IN ('QUEUED', 'RUNNING', 'FINISHED', 'SYSTEM_ERROR', 'CANCELLED')",
    )
    op.add_column("submissions", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("submissions", sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_index("ix_submissions_user_created_at", table_name="submissions")
    op.create_index("ix_submissions_user_created_at", "submissions", ["user_id", "created_at", "id"])
    op.create_index("ix_submissions_status_created_at", "submissions", ["status", "created_at"])
    op.create_index("ix_submissions_problem_verdict", "submissions", ["problem_slug", "verdict"])
    op.create_index("ix_submissions_user_status_created", "submissions", ["user_id", "status", "created_at"])
    op.create_index("ix_users_active_created", "users", ["is_active", "created_at"])
    op.create_index("ix_problems_catalog", "problems", ["status", "category", "difficulty", "topic", "title"])
    op.create_index("ix_user_progress_leaderboard", "user_progress", ["xp", "updated_at"])
    op.create_index("ix_rank_history_user_reached", "rank_history", ["user_id", "reached_at"])
    op.create_index("ix_learning_path_progress_path", "learning_path_progress", ["path_slug", "enrolled_at"])


def downgrade():
    op.drop_index("ix_learning_path_progress_path", table_name="learning_path_progress")
    op.drop_index("ix_rank_history_user_reached", table_name="rank_history")
    op.drop_index("ix_user_progress_leaderboard", table_name="user_progress")
    op.drop_index("ix_problems_catalog", table_name="problems")
    op.drop_index("ix_users_active_created", table_name="users")
    op.drop_index("ix_submissions_user_status_created", table_name="submissions")
    op.drop_index("ix_submissions_problem_verdict", table_name="submissions")
    op.drop_index("ix_submissions_status_created_at", table_name="submissions")
    op.drop_index("ix_submissions_user_created_at", table_name="submissions")
    op.create_index("ix_submissions_user_created_at", "submissions", ["user_id", "created_at"])
    op.drop_column("submissions", "cancel_requested_at")
    op.drop_column("submissions", "attempt_count")
    op.drop_constraint("submission_status", "submissions", type_="check")
    op.create_check_constraint(
        "submission_status", "submissions",
        "status IN ('QUEUED', 'RUNNING', 'FINISHED', 'SYSTEM_ERROR')",
    )
