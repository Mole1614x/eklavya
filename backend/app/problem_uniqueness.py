"""Conservative duplicate detection for EKLAVYA's shared question bank.

Only block strong matches. Two problems covering the same general concept are
not necessarily duplicates when their input contract or technology differs.
"""
from __future__ import annotations

import re
from typing import Any, Iterable


# Legacy seed entries already shipped with different slugs. They must remain
# addressable because learner submissions or assessments may reference them.
LEGACY_EQUIVALENTS = {
    frozenset({"first-occurrence", "binary-search-index"}),
}


def normalized(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def family(question: Any) -> str:
    category = field(question, "category")
    topic = field(question, "topic")
    if category in {"foundations", "code"}:
        return "programming"
    if topic.lower().startswith("numpy"):
        return "numpy"
    if topic.lower().startswith("pandas"):
        return "pandas"
    return str(category)


def field(question: Any, key: str) -> Any:
    return question.get(key, "") if isinstance(question, dict) else getattr(question, key, "")


def duplicate_reason(candidate: Any, existing: Any) -> str | None:
    if field(candidate, "slug") == field(existing, "slug"):
        return None
    if field(candidate, "format") != field(existing, "format"):
        return None
    if family(candidate) != family(existing):
        return None

    title_left = normalized(field(candidate, "title"))
    title_right = normalized(field(existing, "title"))
    if title_left and title_left == title_right:
        return "same normalized title and question type"

    # Only exact normalized statements are safe to block automatically:
    # "create ten ones" and "create ten zeros" are NOT the same task.
    description_left = normalized(field(candidate, "description"))
    description_right = normalized(field(existing, "description"))
    if len(description_left) >= 65 and description_left == description_right:
        return "identical normalized problem statement"

    # First Occurrence and Binary Search are already the same first-index
    # objective and input contract. This pair is audited as legacy.
    slugs = frozenset({field(candidate, "slug"), field(existing, "slug")})
    if slugs in LEGACY_EQUIVALENTS:
        return "equivalent first-occurrence search contract"
    return None


def find_duplicates(candidate: Any, existing: Iterable[Any]) -> list[dict[str, str]]:
    return [
        {"slug": field(other, "slug"), "title": field(other, "title"), "reason": reason}
        for other in existing
        if (reason := duplicate_reason(candidate, other)) is not None
    ]


def check_seed_duplicates(items: list[Any]) -> None:
    """Reject newly duplicated content before DB writes; allow identified legacy pairs."""
    unique_slugs = set()
    for i, item in enumerate(items):
        slug = field(item, "slug")
        if slug in unique_slugs:
            raise ValueError(f"Repeated question slug in seed packs: {slug}")
        unique_slugs.add(slug)
        for collision in find_duplicates(item, items[:i]):
            if frozenset({slug, collision["slug"]}) not in LEGACY_EQUIVALENTS:
                raise ValueError(
                    f"Question {slug} duplicates {collision['slug']}: {collision['reason']}. "
                    "Reuse the existing question slug in the learning path, "
                    "or replace this proposed question with a distinct challenge."
                )
