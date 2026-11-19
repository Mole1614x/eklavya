from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SubmissionMode = Literal["RUN", "SUBMIT"]


class SubmissionCreate(BaseModel):
    language: str = Field(min_length=1, max_length=24, pattern=r"^[a-z0-9+#-]+$")
    source_code: str = Field(min_length=1, max_length=100_000)
    mode: SubmissionMode = "SUBMIT"


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    problem_slug: str
    language: str
    mode: str
    status: str
    verdict: str | None
    output: str | None
    execution_ms: int | None
    memory_kb: int | None
    passed_tests: int
    total_tests: int
    created_at: datetime
    finished_at: datetime | None


class TestCaseWrite(BaseModel):
    input_data: str = Field(max_length=50_000)
    expected_output: str = Field(max_length=50_000)
    is_hidden: bool = True
    position: int = Field(default=0, ge=0)
    tolerance: float | None = Field(default=None, gt=0)


class ProblemAdminWrite(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=24)
    difficulty: Literal["Beginner", "Easy", "Medium", "Hard"]
    format: Literal["CODE", "EXPRESSION", "SQL_QUERY", "NUMERICAL", "MULTIPLE_CHOICE", "DATASET_ANALYSIS"]
    topic: str = Field(min_length=1, max_length=80)
    tags: list[str]
    description: str = Field(min_length=1, max_length=50_000)
    constraints: list[str]
    examples: list[dict[str, str]]
    choices: list[str] = Field(default_factory=list)
    test_cases: list[TestCaseWrite] = Field(default_factory=list)
