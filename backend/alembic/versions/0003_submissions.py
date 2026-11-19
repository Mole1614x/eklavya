"""Add private test cases and submissions."""

import sqlalchemy as sa
from alembic import op

revision = "0003_submissions"
down_revision = "0002_auth"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("input_data", sa.Text, nullable=False, server_default=""),
        sa.Column("expected_output", sa.Text, nullable=False),
        sa.Column("is_hidden", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tolerance", sa.Float),
    )
    op.create_index("ix_test_cases_problem_slug", "test_cases", ["problem_slug"])
    op.create_table(
        "submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="RESTRICT"), nullable=False),
        sa.Column("language", sa.String(24), nullable=False),
        sa.Column("source_code", sa.Text, nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="QUEUED"),
        sa.Column("verdict", sa.String(32)), sa.Column("output", sa.Text),
        sa.Column("execution_ms", sa.Integer), sa.Column("memory_kb", sa.Integer),
        sa.Column("passed_tests", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tests", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("mode IN ('RUN', 'SUBMIT')", name="submission_mode"),
        sa.CheckConstraint("status IN ('QUEUED', 'RUNNING', 'FINISHED', 'SYSTEM_ERROR')", name="submission_status"),
    )
    op.create_index("ix_submissions_user_id", "submissions", ["user_id"])
    op.create_index("ix_submissions_problem_slug", "submissions", ["problem_slug"])
    op.create_index("ix_submissions_created_at", "submissions", ["created_at"])


def downgrade():
    op.drop_table("submissions")
    op.drop_table("test_cases")
