"""Add contests, registrations, submissions, and ratings."""

import sqlalchemy as sa
from alembic import op

revision = "0008_contests"
down_revision = "0007_daily_paths"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("contests",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("title", sa.String(160), nullable=False), sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_rated", sa.Boolean, nullable=False, server_default=sa.true()))
    op.create_index("ix_contests_slug", "contests", ["slug"], unique=True)
    op.create_index("ix_contests_starts_at", "contests", ["starts_at"])
    op.create_index("ix_contests_ends_at", "contests", ["ends_at"])
    with op.batch_alter_table("submissions") as batch:
        batch.add_column(sa.Column("contest_id", sa.Integer, sa.ForeignKey("contests.id", ondelete="RESTRICT", name="fk_submissions_contest_id")))
    op.create_index("ix_submissions_contest_id", "submissions", ["contest_id"])
    op.create_table("contest_problems",
        sa.Column("contest_id", sa.Integer, sa.ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="RESTRICT"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False), sa.Column("points", sa.Integer, nullable=False, server_default="100"))
    op.create_table("contest_registrations",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("contest_id", sa.Integer, sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_registration"))
    op.create_index("ix_contest_registrations_contest_id", "contest_registrations", ["contest_id"])
    op.create_index("ix_contest_registrations_user_id", "contest_registrations", ["user_id"])
    op.create_table("contest_submissions",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("contest_id", sa.Integer, sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="RESTRICT"), nullable=False),
        sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_contest_submissions_contest_id", "contest_submissions", ["contest_id"])
    op.create_index("ix_contest_submissions_user_id", "contest_submissions", ["user_id"])
    op.create_table("contest_ratings",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("contest_id", sa.Integer, sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating_before", sa.Integer, nullable=False), sa.Column("rating_after", sa.Integer, nullable=False),
        sa.Column("position", sa.Integer, nullable=False), sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_rating"))
    op.create_index("ix_contest_ratings_contest_id", "contest_ratings", ["contest_id"])
    op.create_index("ix_contest_ratings_user_id", "contest_ratings", ["user_id"])


def downgrade():
    op.drop_table("contest_ratings")
    op.drop_table("contest_submissions")
    op.drop_table("contest_registrations")
    op.drop_table("contest_problems")
    op.drop_index("ix_submissions_contest_id", table_name="submissions")
    with op.batch_alter_table("submissions") as batch:
        batch.drop_column("contest_id")
    op.drop_table("contests")
