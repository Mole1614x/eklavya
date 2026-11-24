from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["foundations", "code", "data", "statistics", "big-data", "ai", "excel", "tableau", "linux", "multi-tool"]
Difficulty = Literal["Beginner", "Easy", "Medium", "Hard"]
ProblemFormat = Literal["CODE", "EXPRESSION", "SQL_QUERY", "NUMERICAL", "MULTIPLE_CHOICE", "DATASET_ANALYSIS"]


class ProblemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    title: str
    category: Category
    difficulty: Difficulty
    format: ProblemFormat
    topic: str
    tags: list[str]


class Starter(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: str
    code: str


class Example(BaseModel):
    input: str
    output: str


class ProblemDetail(ProblemSummary):
    description: str
    constraints: list[str]
    examples: list[Example]
    starters: list[Starter]
    choices: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_answer_format(self):
        if self.format == "MULTIPLE_CHOICE":
            if len(self.choices) < 2 or len(set(self.choices)) != len(self.choices):
                raise ValueError("Multiple-choice problems require at least two distinct choices")
        elif self.choices:
            raise ValueError("Only multiple-choice problems can include choices")
        if self.format in {"NUMERICAL", "MULTIPLE_CHOICE"}:
            if self.starters:
                raise ValueError("Numeric and multiple-choice answers do not use starter code")
        elif not self.starters:
            raise ValueError("Programming problems require starter code")
        if len({starter.language for starter in self.starters}) != len(self.starters):
            raise ValueError("Languages must be unique per problem")
        return self


class Catalog(BaseModel):
    items: list[ProblemSummary]
    total: int
    topics: list[str]
    solved_slugs: list[str] = Field(default_factory=list)
