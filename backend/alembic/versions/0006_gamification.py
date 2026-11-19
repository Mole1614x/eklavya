"""Add XP, ranks, progress, and achievements."""

import sqlalchemy as sa
from alembic import op

revision = "0006_gamification"
down_revision = "0005_data_evaluators"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("rank_levels",
        sa.Column("slug", sa.String(32), primary_key=True), sa.Column("name", sa.String(40), nullable=False, unique=True),
        sa.Column("min_xp", sa.Integer, nullable=False, unique=True), sa.Column("stars", sa.Integer, nullable=False),
        sa.Column("position", sa.Integer, nullable=False, unique=True))
    op.create_table("user_progress",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("xp", sa.Integer, nullable=False, server_default="0"), sa.Column("solved_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("current_rank_slug", sa.String(32), sa.ForeignKey("rank_levels.slug"), nullable=False, server_default="shishya"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("xp_transactions",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False), sa.Column("reason", sa.String(120), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False), sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "source_type", "source_id", name="uq_xp_source"))
    op.create_index("ix_xp_transactions_user_id", "xp_transactions", ["user_id"])
    op.create_table("rank_history",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank_slug", sa.String(32), sa.ForeignKey("rank_levels.slug"), nullable=False),
        sa.Column("reached_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_rank_history_user_id", "rank_history", ["user_id"])
    op.create_table("achievements",
        sa.Column("slug", sa.String(64), primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(240), nullable=False), sa.Column("criteria", sa.JSON, nullable=False),
        sa.Column("xp_reward", sa.Integer, nullable=False, server_default="0"))
    op.create_table("user_achievements",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("achievement_slug", sa.String(64), sa.ForeignKey("achievements.slug"), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "achievement_slug", name="uq_user_achievement"))
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])


def downgrade():
    op.drop_table("user_achievements")
    op.drop_table("achievements")
    op.drop_table("rank_history")
    op.drop_table("xp_transactions")
    op.drop_table("user_progress")
    op.drop_table("rank_levels")
