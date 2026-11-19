from sqlalchemy import CheckConstraint, ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint("difficulty IN ('Beginner', 'Easy', 'Medium', 'Hard')", name="problem_difficulty"),
        CheckConstraint(
            "format IN ('CODE', 'EXPRESSION', 'SQL_QUERY', 'NUMERICAL', 'MULTIPLE_CHOICE', 'DATASET_ANALYSIS')",
            name="problem_format",
        ),
    )

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(24), index=True)
    difficulty: Mapped[str] = mapped_column(String(12), index=True)
    format: Mapped[str] = mapped_column(String(24))
    topic: Mapped[str] = mapped_column(String(80), index=True)
    tags: Mapped[list[str]] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text)
    constraints: Mapped[list[str]] = mapped_column(JSON)
    examples: Mapped[list[dict]] = mapped_column(JSON)
    choices: Mapped[list[str]] = mapped_column(JSON)
    starters: Mapped[list["StarterCode"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="StarterCode.language"
    )


class StarterCode(Base):
    __tablename__ = "starter_code"

    problem_slug: Mapped[str] = mapped_column(ForeignKey("problems.slug", ondelete="CASCADE"), primary_key=True)
    language: Mapped[str] = mapped_column(String(24), primary_key=True)
    code: Mapped[str] = mapped_column(Text)
