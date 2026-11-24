"""Authoritative catalogue and auditable mappings for the 45 subject tracks."""
import json

from sqlalchemy import or_

from .config import settings
from .models import Problem

SUBJECTS = json.loads(
    (settings().seed_file.parent / "subject_catalog.json").read_text(encoding="utf-8")
)
assert len(SUBJECTS) == 45
assert len({row["slug"] for row in SUBJECTS}) == 45
assert sum(row["target"] for row in SUBJECTS) == 2500

BY_SLUG = {subject["slug"]: subject for subject in SUBJECTS}
LOGIC_TOPICS = {
    "Basic Programming", "Number Logic", "Patterns", "String Logic",
    "Arrays and Lists", "Searching Sorting and Recursion", "Interview Logic",
}
LOGIC_EXISTING = {"parity-check", "sum-of-digits", "pair-indices", "balanced-delimiters"}


def matched_subject_ids(problem: Problem) -> set[int]:
    ids = {subject["id"] for subject in SUBJECTS if problem.topic == subject["name"]}
    if problem.topic in LOGIC_TOPICS or problem.slug in LOGIC_EXISTING:
        ids.add(1)
    if problem.topic.startswith("NumPy · Level "):
        ids.add(5)
    if problem.topic.startswith("Pandas · Level "):
        ids.add(6)
    if problem.topic.startswith("Practical Data Analysis · Level "):
        ids.add(7)
    return ids


def subject_clause(subject_slug: str):
    """SQL expression matching the same subject classifications as the counter."""
    subject = BY_SLUG.get(subject_slug)
    if subject is None:
        raise ValueError(f"Unknown subject: {subject_slug}")
    expressions = [Problem.topic == subject["name"]]
    if subject["id"] == 1:
        expressions.extend((Problem.topic.in_(LOGIC_TOPICS), Problem.slug.in_(LOGIC_EXISTING)))
    if subject["id"] in {5, 6, 7}:
        expressions.append(Problem.topic.startswith({
            5: "NumPy · Level ", 6: "Pandas · Level ",
            7: "Practical Data Analysis · Level ",
        }[subject["id"]]))
    return or_(*expressions)
