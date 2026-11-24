"""Protect canonical challenges and historical user work from duplicate question seeds."""
from copy import deepcopy
import pytest

from app.problem_uniqueness import check_seed_duplicates, find_duplicates


def sample(slug: str, title: str = "Count Unique Values") -> dict:
    return {
        "slug": slug, "title": title, "category": "code",
        "format": "CODE", "topic": "Arrays",
        "description": "Read an integer array and print its number of distinct elements.",
    }


def test_duplicate_titles_with_different_punctuation_are_rejected():
    original = sample("unique-values")
    duplicate = sample("another-unique", "Count: unique values!")
    assert find_duplicates(duplicate, [original])[0]["slug"] == original["slug"]
    with pytest.raises(ValueError, match="Reuse the existing question slug"):
        check_seed_duplicates([original, duplicate])


def test_same_slug_is_reused_and_distinct_implementation_is_allowed():
    original = sample("unique-values")
    assert not find_duplicates(sample("unique-values"), [original])
    assert not find_duplicates(sample("other", "Count Unique Values") | {
        "category": "data", "topic": "NumPy · Level 2"
    }, [original])


def test_legacy_equivalent_pair_is_preserved_without_new_duplicates():
    old = sample("first-occurrence", "First Occurrence")
    newer = sample("binary-search-index", "Binary Search")
    check_seed_duplicates([old, newer])
    with pytest.raises(ValueError, match="duplicates"):
        check_seed_duplicates([old, newer, sample("duplicate-binary", "Binary Search")])
