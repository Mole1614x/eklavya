"""Add administrative lifecycle, dataset, and audit models."""

import sqlalchemy as sa
from alembic import op

revision = "0010_admin_console"
down_revision = "0009_production_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("problems", sa.Column("status", sa.String(16), nullable=False, server_default="PUBLISHED"))
    op.create_check_constraint(
        "problem_status", "problems", "status IN ('DRAFT', 'PUBLISHED', 'UNPUBLISHED', 'ARCHIVED')",
    )
    op.create_index("ix_problems_status", "problems", ["status"])
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("learning_paths", sa.Column("status", sa.String(16), nullable=False, server_default="PUBLISHED"))
    op.create_check_constraint(
        "learning_path_status", "learning_paths", "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
    )
    op.create_index("ix_learning_paths_status", "learning_paths", ["status"])
    op.add_column(
        "contests", sa.Column("publication_status", sa.String(16), nullable=False, server_default="PUBLISHED"),
    )
    op.create_check_constraint(
        "contest_publication_status", "contests",
        "publication_status IN ('DRAFT', 'PUBLISHED', 'CANCELLED', 'FINALIZED')",
    )
    op.create_index("ix_contests_publication_status", "contests", ["publication_status"])
    op.create_table(
        "managed_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('SQL', 'PANDAS', 'NUMPY', 'STATISTICS', 'PYSPARK', 'MACHINE_LEARNING')",
            name="managed_dataset_kind",
        ),
        sa.UniqueConstraint("name", "version", name="uq_managed_dataset_version"),
    )
    op.create_index("ix_managed_datasets_name", "managed_datasets", ["name"])
    op.create_index("ix_managed_datasets_kind", "managed_datasets", ["kind"])
    op.create_index("ix_managed_datasets_is_active", "managed_datasets", ["is_active"])
    op.create_index("ix_managed_datasets_created_by", "managed_datasets", ["created_by"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("details", sa.JSON, nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_type", "target_id"])


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("managed_datasets")
    op.drop_index("ix_contests_publication_status", table_name="contests")
    op.drop_constraint("contest_publication_status", "contests", type_="check")
    op.drop_column("contests", "publication_status")
    op.drop_index("ix_learning_paths_status", table_name="learning_paths")
    op.drop_constraint("learning_path_status", "learning_paths", type_="check")
    op.drop_column("learning_paths", "status")
    op.drop_column("users", "last_login_at")
    op.drop_index("ix_problems_status", table_name="problems")
    op.drop_constraint("problem_status", "problems", type_="check")
    op.drop_column("problems", "status")
