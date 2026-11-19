"""Add judge execution leases."""

import sqlalchemy as sa
from alembic import op

revision = "0004_judge_leases"
down_revision = "0003_submissions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("submissions", sa.Column("started_at", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("submissions", "started_at")
