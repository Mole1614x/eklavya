"""Add indexes for submission history, insights, and contest standings."""

from alembic import op

revision = "0009_production_indexes"
down_revision = "0008_contests"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_submissions_user_created_at", "submissions", ["user_id", "created_at"])
    op.create_index("ix_xp_transactions_user_created_at", "xp_transactions", ["user_id", "created_at"])
    op.create_index(
        "ix_contest_submissions_standings", "contest_submissions",
        ["contest_id", "user_id", "problem_slug", "submitted_at"],
    )


def downgrade():
    op.drop_index("ix_contest_submissions_standings", table_name="contest_submissions")
    op.drop_index("ix_xp_transactions_user_created_at", table_name="xp_transactions")
    op.drop_index("ix_submissions_user_created_at", table_name="submissions")
