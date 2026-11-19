"""Add pluggable problem evaluators."""

import sqlalchemy as sa
from alembic import op

revision = "0005_data_evaluators"
down_revision = "0004_judge_leases"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "problem_evaluators",
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="CASCADE"), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
    )


def downgrade():
    op.drop_table("problem_evaluators")
