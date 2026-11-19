"""Create the problem catalog."""

import sqlalchemy as sa
from alembic import op

revision = "0001_catalog"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "problems",
        sa.Column("slug", sa.String(100), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("difficulty", sa.String(12), nullable=False),
        sa.Column("format", sa.String(24), nullable=False),
        sa.Column("topic", sa.String(80), nullable=False),
        sa.Column("tags", sa.JSON, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("constraints", sa.JSON, nullable=False),
        sa.Column("examples", sa.JSON, nullable=False),
        sa.Column("choices", sa.JSON, nullable=False),
        sa.CheckConstraint("difficulty IN ('Beginner', 'Easy', 'Medium', 'Hard')", name="problem_difficulty"),
        sa.CheckConstraint(
            "format IN ('CODE', 'EXPRESSION', 'SQL_QUERY', 'NUMERICAL', 'MULTIPLE_CHOICE', 'DATASET_ANALYSIS')",
            name="problem_format",
        ),
    )
    for column in ("category", "difficulty", "topic"):
        op.create_index(f"ix_problems_{column}", "problems", [column])
    op.create_table(
        "starter_code",
        sa.Column("problem_slug", sa.String(100), sa.ForeignKey("problems.slug", ondelete="CASCADE"), primary_key=True),
        sa.Column("language", sa.String(24), primary_key=True),
        sa.Column("code", sa.Text, nullable=False),
    )


def downgrade():
    op.drop_table("starter_code")
    op.drop_table("problems")
