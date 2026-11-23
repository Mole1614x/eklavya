from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProblemStatus = Literal["DRAFT", "PUBLISHED", "UNPUBLISHED", "ARCHIVED"]
ContestPublicationStatus = Literal["DRAFT", "PUBLISHED", "CANCELLED", "FINALIZED"]
PathStatus = Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
DatasetKind = Literal["SQL", "PANDAS", "NUMPY", "STATISTICS", "PYSPARK", "MACHINE_LEARNING"]


class TrendPoint(BaseModel):
    day: str
    count: int


class RecentRegistration(BaseModel):
    username: str
    display_name: str
    created_at: datetime


class AdminOverview(BaseModel):
    total_users: int
    active_users: int
    total_problems: int
    published_problems: int
    total_submissions: int
    accepted_submissions: int
    failed_submissions: int
    active_contests: int
    queued_submissions: int
    running_submissions: int
    stuck_submissions: int
    cancelled_submissions: int
    average_queue_ms: float | None
    average_execution_ms: float | None
    registration_trend: list[TrendPoint]
    submission_trend: list[TrendPoint]
    recent_registrations: list[RecentRegistration]


class JudgeRecoveryRead(BaseModel):
    recovered: int
    cancelled: int
    failed_to_enqueue: int


class AdminStarterWrite(BaseModel):
    language: str = Field(min_length=1, max_length=24, pattern=r"^[a-z0-9+#-]+$")
    code: str = Field(max_length=100_000)


class AdminTestCaseWrite(BaseModel):
    input_data: str = Field(max_length=50_000)
    expected_output: str = Field(max_length=50_000)
    is_hidden: bool = True
    position: int = Field(default=0, ge=0)
    tolerance: float | None = Field(default=None, gt=0)


class AdminEvaluatorWrite(BaseModel):
    kind: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_]+$")
    config: dict = Field(default_factory=dict)


class AdminProblemWrite(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=24, pattern=r"^[a-z0-9-]+$")
    difficulty: Literal["Beginner", "Easy", "Medium", "Hard"]
    format: Literal["CODE", "EXPRESSION", "SQL_QUERY", "NUMERICAL", "MULTIPLE_CHOICE", "DATASET_ANALYSIS"]
    topic: str = Field(min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=30)
    description: str = Field(min_length=1, max_length=50_000)
    constraints: list[str] = Field(default_factory=list, max_length=100)
    examples: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    choices: list[str] = Field(default_factory=list, max_length=20)
    status: ProblemStatus = "DRAFT"
    access_scope: Literal["ALL", "SELECTED"] = "ALL"
    assigned_user_ids: list[int] = Field(default_factory=list, max_length=1000)
    starters: list[AdminStarterWrite] = Field(default_factory=list, max_length=10)
    test_cases: list[AdminTestCaseWrite] = Field(default_factory=list, max_length=200)
    evaluator: AdminEvaluatorWrite | None = None

    @model_validator(mode="after")
    def validate_contract(self):
        if self.status == "PUBLISHED" and not self.test_cases:
            raise ValueError("Published problems require at least one test case")
        if self.format == "MULTIPLE_CHOICE" and len(self.choices) < 2:
            raise ValueError("Multiple-choice problems require at least two choices")
        languages = [starter.language for starter in self.starters]
        if len(languages) != len(set(languages)):
            raise ValueError("Starter languages must be unique")
        return self


class ProblemStatusUpdate(BaseModel):
    status: ProblemStatus
    reason: str = Field(min_length=3, max_length=240)


class AdminProblemRead(BaseModel):
    slug: str
    title: str
    category: str
    difficulty: str
    format: str
    topic: str
    status: str
    access_scope: Literal["ALL", "SELECTED"]
    assigned_count: int
    supported_languages: list[str]
    test_case_count: int
    hidden_test_count: int


class AdminProblemDetail(AdminProblemRead):
    tags: list[str]
    description: str
    constraints: list[str]
    examples: list[dict]
    choices: list[str]
    starters: list[AdminStarterWrite]
    test_cases: list[AdminTestCaseWrite]
    evaluator: AdminEvaluatorWrite | None


class DatasetUpload(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.-]*$")
    kind: DatasetKind
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    content_base64: str = Field(min_length=1)


class AdminDatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    kind: str
    version: int
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    is_active: bool
    created_by: int
    created_at: datetime


class DatasetStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(min_length=3, max_length=240)


class AdminUserRead(BaseModel):
    id: int
    email: str
    username: str
    display_name: str
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login_at: datetime | None
    submissions: int
    accepted_submissions: int
    system_errors: int


class UserStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(min_length=3, max_length=240)


class AdminContestProblemWrite(BaseModel):
    problem_slug: str = Field(min_length=1, max_length=100)
    points: int = Field(default=100, ge=1, le=10_000)


class AdminContestWrite(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    starts_at: datetime
    ends_at: datetime
    is_rated: bool = True
    publication_status: ContestPublicationStatus = "DRAFT"
    access_scope: Literal["ALL", "SELECTED"] = "ALL"
    assigned_user_ids: list[int] = Field(default_factory=list, max_length=1000)
    problems: list[AdminContestProblemWrite] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Contest end must be after its start")
        slugs = [problem.problem_slug for problem in self.problems]
        if len(slugs) != len(set(slugs)):
            raise ValueError("Contest problems must be unique")
        return self


class ContestStatusUpdate(BaseModel):
    status: ContestPublicationStatus
    reason: str = Field(min_length=3, max_length=240)


class AdminContestRead(BaseModel):
    slug: str
    title: str
    starts_at: datetime
    ends_at: datetime
    is_rated: bool
    publication_status: str
    access_scope: Literal["ALL", "SELECTED"]
    assigned_count: int
    registrations: int
    submissions: int
    problem_count: int


class AdminContestRegistrationRead(BaseModel):
    user_id: int
    username: str
    display_name: str
    registered_at: datetime


class AdminContestSubmissionRead(BaseModel):
    submission_id: str
    username: str
    problem_slug: str
    language: str
    status: str
    verdict: str | None
    submitted_at: datetime


class AdminContestStandingRead(BaseModel):
    position: int
    username: str
    display_name: str
    score: int
    solved: int
    penalty_seconds: int


class AdminPathProblemWrite(BaseModel):
    problem_slug: str = Field(min_length=1, max_length=100)
    milestone: str | None = Field(default=None, max_length=120)


class AdminPathWrite(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(max_length=500)
    prerequisites: list[str] = Field(default_factory=list, max_length=20)
    status: PathStatus = "DRAFT"
    access_scope: Literal["ALL", "SELECTED"] = "ALL"
    assigned_user_ids: list[int] = Field(default_factory=list, max_length=1000)
    problems: list[AdminPathProblemWrite] = Field(default_factory=list, max_length=100)


class AdminPathRead(BaseModel):
    slug: str
    title: str
    status: str
    access_scope: Literal["ALL", "SELECTED"]
    assigned_count: int
    prerequisites: list[str]
    problem_count: int
    enrollments: int


class AdminAchievementWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=240)
    criteria: dict
    xp_reward: int = Field(default=0, ge=0, le=10_000)


class AdminAchievementRead(BaseModel):
    slug: str
    name: str
    description: str
    criteria: dict
    xp_reward: int
    awarded_count: int


class AdminXPTransactionRead(BaseModel):
    id: int
    username: str
    amount: int
    reason: str
    source_type: str
    source_id: str
    created_at: datetime


class AdminRankHistoryRead(BaseModel):
    id: int
    username: str
    rank_slug: str
    reached_at: datetime


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    actor_username: str | None
    action: str
    target_type: str
    target_id: str
    details: dict
    ip_address: str | None
    created_at: datetime
