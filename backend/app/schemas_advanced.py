from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


AssessmentType = Literal["CODING", "DSA", "SQL", "PANDAS", "STATISTICS", "DATA_ENGINEERING", "EXCEL", "TABLEAU", "LINUX", "MIXED"]


class AssessmentQuestionWrite(BaseModel):
    problem_slug: str = Field(min_length=1, max_length=100)
    points: int = Field(default=100, ge=1, le=10_000)


class AssessmentWrite(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=1000)
    instructions: str = Field(default="", max_length=10_000)
    assessment_type: AssessmentType
    duration_minutes: int = Field(ge=1, le=480)
    opens_at: datetime
    closes_at: datetime
    max_attempts: int = Field(default=1, ge=1, le=20)
    penalty_percent: float = Field(default=0, ge=0, le=100)
    release_results: bool = False
    status: Literal["DRAFT", "PUBLISHED", "UNPUBLISHED"] = "DRAFT"
    access_scope: Literal["ALL", "SELECTED"] = "SELECTED"
    template_key: str | None = Field(default=None, max_length=40)
    questions: list[AssessmentQuestionWrite] = Field(min_length=1, max_length=100)
    assigned_user_ids: list[int] = Field(default_factory=list, max_length=1000)
    assigned_group_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def valid_window(self):
        if self.closes_at <= self.opens_at:
            raise ValueError("Assessment close time must be after its open time")
        if len({item.problem_slug for item in self.questions}) != len(self.questions):
            raise ValueError("Assessment questions must be unique")
        if len(set(self.assigned_user_ids)) != len(self.assigned_user_ids):
            raise ValueError("Assessment assignments must be unique")
        if len(set(self.assigned_group_ids)) != len(self.assigned_group_ids):
            raise ValueError("Assessment group assignments must be unique")
        return self


class LearnerGroupWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    user_ids: list[int] = Field(default_factory=list, max_length=1000)


class AssessmentTemplateCreate(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    opens_at: datetime
    closes_at: datetime
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    difficulty: Literal["Beginner", "Easy", "Medium", "Hard"] | None = None
    question_slugs: list[str] = Field(default_factory=list, max_length=100)
    assigned_user_ids: list[int] = Field(default_factory=list, max_length=1000)
    assigned_group_ids: list[str] = Field(default_factory=list, max_length=100)
    access_scope: Literal["ALL", "SELECTED"] = "SELECTED"
    release_results: bool = False


class AssessmentStatusWrite(BaseModel):
    status: Literal["DRAFT", "PUBLISHED", "UNPUBLISHED", "ARCHIVED"]
    reason: str = Field(min_length=3, max_length=500)


class AssessmentRead(BaseModel):
    id: str
    title: str
    description: str
    instructions: str
    assessment_type: str
    duration_minutes: int
    opens_at: datetime
    closes_at: datetime
    max_attempts: int
    penalty_percent: float
    release_results: bool
    status: str
    template_key: str | None
    access_scope: Literal["ALL", "SELECTED"]
    assigned_user_ids: list[int] = Field(default_factory=list)
    assigned_group_ids: list[str] = Field(default_factory=list)
    questions: list[dict[str, Any]]
    assigned_count: int
    attempt_count: int


class AttemptRead(BaseModel):
    id: str
    assessment_id: str
    assessment_title: str
    attempt_number: int
    status: str
    started_at: datetime
    deadline_at: datetime
    server_time: datetime
    finalized_at: datetime | None
    score: float | None = None
    max_score: float | None = None
    questions: list[dict[str, Any]] = Field(default_factory=list)
    answers: list[dict[str, Any]] = Field(default_factory=list)


class AnswerWrite(BaseModel):
    problem_slug: str = Field(min_length=1, max_length=100)
    answer: str = Field(default="", max_length=100_000)
    language: str | None = Field(default=None, max_length=24)
    submission_id: str | None = Field(default=None, max_length=36)


class DatasetUpload(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    category: str = Field(default="Personal", min_length=1, max_length=32)
    difficulty: Literal["Beginner", "Easy", "Medium", "Hard"] = "Beginner"
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    content_base64: str = Field(min_length=1)
    publish: bool = False
    download_allowed: bool = True


class DatasetRead(BaseModel):
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    format: str
    original_filename: str
    size_bytes: int
    status: str
    version: int
    download_allowed: bool
    column_info: list[dict[str, Any]]
    profile: dict[str, Any]
    transformations: list[dict[str, Any]]
    created_at: datetime
    owned_by_current_user: bool


class DatasetTransform(BaseModel):
    operation: Literal["drop_duplicates", "drop_missing", "fill_missing", "convert_type", "normalize", "standardize_dates", "rename_column"]
    column: str | None = Field(default=None, max_length=120)
    value: str | int | float | bool | None = None
    target_type: Literal["string", "integer", "number", "boolean"] | None = None
    new_name: str | None = Field(default=None, max_length=120)


class DatasetPracticeWrite(BaseModel):
    technology: Literal["PANDAS", "NUMPY", "SQL"]
    source_code: str = Field(min_length=1, max_length=100_000)


class DatasetPracticeRead(BaseModel):
    id: str
    dataset_id: str
    technology: str
    status: str
    output: str | None
    execution_ms: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ExpressionSubmission(BaseModel):
    expression: str = Field(min_length=1, max_length=2000)
    cells: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)
    fields: list[str] = Field(default_factory=list, max_length=200)
    expected: Any | None = None
    partition_by: list[str] = Field(default_factory=list, max_length=20)
    order_by: str | None = Field(default=None, max_length=120)


class WorkbookSubmission(BaseModel):
    challenge_key: Literal["regional-sales"]
    filename: str = Field(min_length=1, max_length=255, pattern=r"^[^/\\]+\.xlsx$")
    content_base64: str = Field(min_length=1)
    answer_cell: str = Field(default="F2", pattern=r"^[A-Z]{1,3}[1-9][0-9]{0,5}$")


class EvaluationRead(BaseModel):
    valid: bool
    passed: bool | None = None
    result: Any | None = None
    feedback: str
    supported_subset: list[str] = Field(default_factory=list)


class MultiToolSubmission(BaseModel):
    challenge_key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    technology: Literal["SQL", "PANDAS", "PYSPARK", "EXCEL", "TABLEAU"]
    answer: str = Field(min_length=1, max_length=20_000)


class AnalyticsRead(BaseModel):
    totals: dict[str, int | float]
    subjects: list[dict[str, Any]]
    daily: list[dict[str, Any]]
    weak_topics: list[str]
