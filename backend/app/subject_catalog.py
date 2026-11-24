"""Authoritative source-controlled catalogue for requested 45 subject tracks."""
import json

from .config import settings

SUBJECTS = json.loads(
    (settings().seed_file.parent / "subject_catalog.json").read_text(encoding="utf-8")
)

assert len(SUBJECTS) == 45
assert len({row["slug"] for row in SUBJECTS}) == len(SUBJECTS)
assert sum(row["target"] for row in SUBJECTS) == 2500
