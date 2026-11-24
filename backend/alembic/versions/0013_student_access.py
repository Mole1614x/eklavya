"""Introduce safe, independent ALL / SELECTED student visibility.

Preexisting assessments stay SELECTED; their direct and group assignments are
left intact. Existing published general content was already publicly visible
and stays ALL. PRIVATE dataset status is unaffected.
"""
import sqlalchemy as sa
from alembic import op

revision = "0013_student_access"
down_revision = "0012_advanced_practice"
branch_labels = None
depends_on = None

def upgrade():
    for table, default in (
        ("problems", "ALL"),
        ("learning_paths", "ALL"),
        ("contests", "ALL"),
        ("assessments", "SELECTED"),
        ("practice_datasets", "ALL"),
    ):
        op.add_column(table, sa.Column("access_scope", sa.String(8), nullable=False, server_default=default))
        op.create_check_constraint(f"ck_{table}_access_scope", table, "access_scope IN ('ALL', 'SELECTED')")
    op.create_table(
        "content_assignments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("content_type", sa.String(16), nullable=False),
        sa.Column("content_id", sa.String(100), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("content_type", "content_id", "user_id", name="uq_content_assignment"),
        sa.CheckConstraint("content_type IN ('problem', 'contest', 'path', 'dataset')", name="content_assignment_type"),
    )
    op.create_index("ix_content_assignments_user_id", "content_assignments", ["user_id"])
    op.create_index("ix_content_assignment_target", "content_assignments", ["content_type", "content_id", "user_id"])

def downgrade():
    op.drop_table("content_assignments")
    for table in ("practice_datasets", "assessments", "contests", "learning_paths", "problems"):
        op.drop_constraint(f"ck_{table}_access_scope", table, type_="check")
        op.drop_column(table, "access_scope")
