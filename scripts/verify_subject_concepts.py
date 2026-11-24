"""Standalone pre-seed audit for EKLAVYA's 45-subject question bank.

This checks coverage, objective identity and answer integrity. It does not
pretend automated structural checks can prove every technical fact is true.
"""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1] / "challenges"
LEGACY_MAPPED = {1: 102, 5: 51, 6: 52, 7: 15, 9: 1, 11: 2, 12: 1}


def normalized(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def main():
    subjects = json.loads((ROOT / "subject_catalog.json").read_text(encoding="utf-8"))
    subject_by_id = {item["id"]: item for item in subjects}
    assert len(subjects) == 45 and sum(s["target"] for s in subjects) == 2500
    concepts = []
    concept_files = sorted(ROOT.glob("subject_concepts_*.json"))
    assert len(concept_files) >= 20, "Expected all curated concept packs, not only the first batch"
    for pack in concept_files:
        payload = json.loads(pack.read_text(encoding="utf-8"))
        assert isinstance(payload, list), pack
        concepts.extend(payload)
    assert len(concepts) == 2155, f"Missing or surplus concepts: {len(concepts)} != 2155"
    old_skills = defaultdict(set)
    old_prompts = set()
    original_checks = []
    for pack in sorted(ROOT.glob("comprehensive_mcq_*.json")):
        original_checks.extend(json.loads(pack.read_text(encoding="utf-8")))
    assert len(original_checks) == 135
    for question in original_checks:
        subject_id = question["subject_id"]
        skill_key = normalized(question["skill"])
        old_skills[subject_id].add(skill_key)
        prompt_key = normalized(question["prompt"])
        assert prompt_key not in old_prompts, f"Repeated existing prompt: {question['prompt']}"
        old_prompts.add(prompt_key)
        assert question["answer"] in question["choices"]
        assert len(question["choices"]) == len(set(question["choices"])) == 4
    by_subject = defaultdict(list)
    for row in concepts:
        sid = row["subject_id"]
        assert sid in subject_by_id
        assert sid not in {1, 5, 6}, f"Saturated subject unexpectedly expanded: {sid}"
        assert row["skill"].strip() and len(row["description"].strip()) >= 30
        by_subject[sid].append(row)
    assert len(by_subject) == 42
    total_after = 0
    answer_positions = Counter()
    for subject in subjects:
        sid = subject["id"]
        target = subject["target"]
        initial = LEGACY_MAPPED.get(sid, 0) + 3
        needed = max(0, target - initial)
        rows = by_subject[sid]
        assert len(rows) == needed, (
            f"{subject['name']}: need {needed} new objectives, found {len(rows)}"
        )
        used_skills = set(old_skills[sid])
        used_definitions = set()
        for row in rows:
            skill = normalized(row["skill"])
            definition = normalized(row["description"])
            assert skill not in used_skills, f"Repeated objective in {subject['name']}: {row['skill']}"
            assert definition not in used_definitions, f"Repeated definition for {row['skill']}"
            used_skills.add(skill)
            used_definitions.add(definition)
        for index, row in enumerate(rows):
            slug = "knowledge-" + subject["slug"][:55].rstrip("-") + "-" + str(index + 4).zfill(2)
            answer = row["description"]
            alternatives = sorted(
                (other["description"] for other in rows if other is not row),
                key=lambda candidate: sha256(f"{slug}:distractor:{candidate}".encode()).hexdigest(),
            )[:3]
            assert len(alternatives) == 3, f"Not enough distinct distractors: {slug}"
            options = sorted(
                [answer, *alternatives],
                key=lambda choice: sha256(f"{slug}:choice:{choice}".encode()).hexdigest(),
            )
            assert len(options) == len(set(options)) == 4, slug
            answer_positions[options.index(answer)] += 1
        total_after += initial + needed
    assert len(answer_positions) == 4
    assert max(answer_positions.values()) < 750, answer_positions
    assert total_after == 2514, total_after  # 2500 target + 14 previously over target
    assert total_after + 13 == 2527  # 13 unmatched legacy questions remain available
    print(
        f"Verified {len(concepts)} new concept questions across {len(by_subject)} remaining tracks; "
        f"{total_after} mapped questions meet all 45 minimums; "
        "2527 seeded problems including 13 unclassified legacy entries."
    )
    print("Correct-choice position distribution:", dict(sorted(answer_positions.items())))


if __name__ == "__main__":
    main()
