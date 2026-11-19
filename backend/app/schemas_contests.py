from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ContestCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    starts_at: datetime
    ends_at: datetime
    is_rated: bool = True
    problems: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def valid_window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Contest end must be after its start")
        if len(set(self.problems)) != len(self.problems):
            raise ValueError("Contest problems must be unique")
        return self


class ContestSummary(BaseModel):
    slug: str
    title: str
    description: str
    starts_at: datetime
    ends_at: datetime
    status: str
    is_rated: bool


class ContestProblemRead(BaseModel):
    slug: str
    title: str
    difficulty: str
    position: int
    points: int


class ContestDetail(ContestSummary):
    problems: list[ContestProblemRead]


class ContestStanding(BaseModel):
    position: int
    username: str
    display_name: str
    score: int
    solved: int
    penalty_seconds: int


class ContestParticipant(BaseModel):
    registered: bool
    rating: int
    submissions: int


class ContestHistoryItem(BaseModel):
    slug: str
    title: str
    position: int
    rating_before: int
    rating_after: int
    delta: int
    ended_at: datetime


class ContestCreated(BaseModel):
    slug: str
