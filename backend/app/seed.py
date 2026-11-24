import json

from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from .config import settings
from .database import Session
from .models import Achievement, Contest, ContestProblem, DailyChallenge, LearningPath, LearningPathProblem, Problem, ProblemEvaluator, RankLevel, StarterCode, TestCase
from .schemas import ProblemDetail
from .problem_uniqueness import check_seed_duplicates


def seed(db: DatabaseSession) -> int:
    # Keep the original catalog stable and load the curated logic packs alongside it.
    # A separate pack prevents overwriting established questions and their judge cases.
    source = json.loads(settings().seed_file.read_text())
    test_cases = json.loads(settings().test_seed_file.read_text()) if settings().test_seed_file.exists() else {}
    logic_ids: dict[int, str] = {}
    seen = {item["slug"] for item in source}
    for pack in sorted(settings().seed_file.parent.glob("logic_levels_*.json")):
        for item in json.loads(pack.read_text()):
            slug = item["slug"]
            if slug in seen:
                raise ValueError(f"Logic catalog slug duplicates existing content: {slug}")
            seen.add(slug)
            logic_ids[item["number"]] = slug
            test_cases[slug] = item["test_cases"]
            source.append({key: value for key, value in item.items() if key not in {"number", "test_cases"}})
    # Data science practice: all 115 prompts use the existing data category and
    # isolated reference-graded solve(data) evaluator. Do not expose references
    # through learner-facing problem details or public judge cases.
    data_practice: dict[str, dict] = {}
    practice_levels: dict[str, dict[int, list[str]]] = {
        "numpy": {}, "pandas": {}, "data_analysis": {},
    }
    for pack_name in ("numpy", "pandas", "data_analysis"):
        pack = settings().seed_file.parent / f"{pack_name}_practice.json"
        if not pack.exists():
            continue
        questions = json.loads(pack.read_text(encoding="utf-8"))
        expected = 15 if pack_name == "data_analysis" else 50
        if len(questions) != expected:
            raise ValueError(f"{pack.name} must contain {expected} practice questions")
        for item in questions:
            slug = item["slug"]
            if slug in seen:
                raise ValueError(f"Duplicate data practice slug: {slug}")
            seen.add(slug)
            reference_source = item["reference_source"]
            compile(reference_source, f"{slug}.py", "exec")
            data_practice[slug] = {
                "kind": "data_practice_function",
                "config": {
                    "function": "solve", "output": "json",
                    "reference_source": reference_source,
                    "tolerance": 1e-6,
                },
            }
            cases = []
            for position, input_value in enumerate(item["test_inputs"]):
                cases.append({
                    "input_data": json.dumps(input_value, allow_nan=False),
                    "expected_output": "null", # reference result computed in isolated judge
                    "is_hidden": position != 0, "position": position,
                })
            test_cases[slug] = cases
            level_label = item["topic"].rsplit("Level ", 1)
            if len(level_label) != 2:
                raise ValueError(f"Data practice level missing for {slug}")
            level = int(level_label[1])
            practice_levels[pack_name].setdefault(level, []).append(slug)
            source.append({key: value for key, value in item.items()
                           if key not in {"number", "test_inputs", "reference_source"}})
    from hashlib import sha256
    # Verified conceptual checks use the existing MULTIPLE_CHOICE evaluator.
    # One genuine answer per question; never seed placeholder test cases.
    from .subject_catalog import SUBJECTS
    subject_by_id = {subject["id"]: subject for subject in SUBJECTS}
    subject_questions: dict[str, list[str]] = {s["slug"]: [] for s in SUBJECTS}
    for pack in sorted(settings().seed_file.parent.glob("comprehensive_mcq_*.json")):
        for item in json.loads(pack.read_text(encoding="utf-8")):
            subject = subject_by_id[item["subject_id"]]
            slug = "knowledge-" + subject["slug"][:55].rstrip("-") + "-" + str(len(subject_questions[subject["slug"]]) + 1).zfill(2)
            if slug in seen:
                raise ValueError(f"Duplicate comprehensive question slug: {slug}")
            answer = item["answer"]
            choices = item["choices"]
            if len(choices) != 4 or len(set(choices)) != 4 or answer not in choices:
                raise ValueError(f"Invalid answer/options for {slug}")
            if not item["prompt"].strip() or not item["skill"].strip():
                raise ValueError(f"Missing meaningful question statement: {slug}")
            seen.add(slug)
            subject_questions[subject["slug"]].append(slug)
            # Shuffle positions reproducibly; correct answers must not always
            # be option A. The actual expected answer is kept in a hidden test.
            arranged_choices = sorted(
                choices, key=lambda choice: sha256(f"{slug}:{choice}".encode()).hexdigest()
            )
            source.append({
                "slug": slug, "title": f'{subject["name"]}: {item["skill"]}',
                "category": subject["category"], "difficulty": "Easy",
                "format": "MULTIPLE_CHOICE", "topic": subject["name"],
                "tags": [f'Subject:{subject["slug"]}', "Knowledge Check"],
                "description": item["prompt"], "constraints": ["Select exactly one correct answer."],
                "examples": [], "starters": [], "choices": arranged_choices,
            })
            test_cases[slug] = [{
                "input_data": "{}", "expected_output": json.dumps(answer),
                "is_hidden": True, "position": 0,
            }]
            data_practice[slug] = {"kind": "multiple_choice", "config": {}}
    # Additional distinct subject knowledge checks. Each definition is a
    # separately authored learning objective; alternatives are other factual
    # descriptions from the same subject rather than recycled number variants.
    # Three existing tracks have already met their minimum, so new content
    # targets only the 42 subjects with verified outstanding question gaps.
    from .problem_uniqueness import normalized
    concept_rows: list[dict] = []
    for pack in sorted(settings().seed_file.parent.glob("subject_concepts_*.json")):
        concept_rows.extend(json.loads(pack.read_text(encoding="utf-8")))
    by_subject: dict[int, list[dict]] = {}
    for item in concept_rows:
        sid = item["subject_id"]
        if sid not in subject_by_id or sid in {1, 5, 6}:
            raise ValueError(f"Concept assigned to completed or unknown subject: {sid}")
        if len(item["skill"].strip()) < 3 or len(item["description"].strip()) < 30:
            raise ValueError(f"Concept lacks a meaningful description: {item}")
        by_subject.setdefault(sid, []).append(item)
    if len(concept_rows) != 840 or len(by_subject) != 42:
        raise ValueError("Subject concept bank must cover 42 remaining subjects with 20 unique concepts each")
    for sid, concepts in sorted(by_subject.items()):
        if len(concepts) != 20:
            raise ValueError(f"Expected 20 concepts for subject {sid}, got {len(concepts)}")
        existing_skills = {
            normalized(entry["title"].split(": ", 1)[-1])
            for entry in source if entry["topic"] == subject_by_id[sid]["name"]
        }
        seen_skills: set[str] = set()
        seen_definitions: set[str] = set()
        for item in concepts:
            skill_key = normalized(item["skill"])
            definition_key = normalized(item["description"])
            if skill_key in existing_skills or skill_key in seen_skills:
                raise ValueError(f"Duplicate learning objective for subject {sid}: {item['skill']}")
            if definition_key in seen_definitions:
                raise ValueError(f"Duplicate concept definition in subject {sid}: {item['skill']}")
            seen_skills.add(skill_key)
            seen_definitions.add(definition_key)
        subject = subject_by_id[sid]
        for item in concepts:
            slug = (
                "knowledge-" + subject["slug"][:55].rstrip("-")
                + "-" + str(len(subject_questions[subject["slug"]]) + 1).zfill(2)
            )
            if slug in seen:
                raise ValueError(f"Repeated concept slug: {slug}")
            seen.add(slug)
            correct = item["description"]
            alternatives = sorted(
                (other["description"] for other in concepts if other is not item),
                key=lambda candidate: sha256(f"{slug}:distractor:{candidate}".encode()).hexdigest(),
            )[:3]
            choices = sorted(
                [correct, *alternatives],
                key=lambda choice: sha256(f"{slug}:choice:{choice}".encode()).hexdigest(),
            )
            if len(set(choices)) != 4:
                raise ValueError(f"Ambiguous repeated answer choice: {slug}")
            title = f'{subject["name"]}: {item["skill"]}'
            source.append({
                "slug": slug, "title": title,
                "category": subject["category"], "difficulty": "Medium",
                "format": "MULTIPLE_CHOICE", "topic": subject["name"],
                "tags": [f'Subject:{subject["slug"]}', "Concept Application"],
                "description": (
                    f'Which description best matches "{item["skill"]}" '
                    f'in {subject["name"]}?'
                ),
                "constraints": ["Select the single most accurate definition of the named concept."],
                "examples": [], "starters": [], "choices": choices,
            })
            test_cases[slug] = [{
                "input_data": "{}", "expected_output": json.dumps(correct),
                "is_hidden": True, "position": 0,
            }]
            data_practice[slug] = {"kind": "multiple_choice", "config": {}}
            subject_questions[subject["slug"]].append(slug)
    check_seed_duplicates(source)
    entries = [ProblemDetail.model_validate(item) for item in source]
    evaluators = json.loads(settings().evaluator_seed_file.read_text()) if settings().evaluator_seed_file.exists() else {}
    gamification = json.loads(settings().gamification_seed_file.read_text()) if settings().gamification_seed_file.exists() else {"ranks": [], "achievements": []}
    for rank in gamification["ranks"]:
        db.merge(RankLevel(**rank))
    for achievement in gamification["achievements"]:
        db.merge(Achievement(**achievement))
    evaluators.update(data_practice)
    for entry in entries:
        problem = db.merge(Problem(
            **entry.model_dump(exclude={"starters"}),
            starters=[StarterCode(**starter.model_dump()) for starter in entry.starters],
        ))
        if entry.slug in test_cases:
            problem.test_cases = [TestCase(**case) for case in test_cases[entry.slug]]
        if entry.slug in evaluators:
            db.merge(ProblemEvaluator(problem_slug=entry.slug, **evaluators[entry.slug]))
    paths = json.loads(settings().learning_paths_seed_file.read_text()) if settings().learning_paths_seed_file.exists() else []
    for path in paths:
        problems = path.pop("problems")
        db.merge(LearningPath(**path))
        for position, problem_slug in enumerate(problems, 1):
            db.merge(LearningPathProblem(path_slug=path["slug"], problem_slug=problem_slug, position=position, milestone="Path complete" if position == len(problems) else None))
    # Structured level-by-level learning paths use the exact problem slugs from the
    # curriculum; existing equivalent problems retain their original identities.
    existing_equivalents = {
        1: "parity-check", 17: "sum-of-digits",
        91: "pair-indices", 92: "balanced-delimiters",
    }
    problem_ids = {**logic_ids, **existing_equivalents}
    levels = [
        (1, "Basic Programming", range(1, 16)),
        (2, "Number-Based Logic", range(16, 36)),
        (3, "Pattern Programming", range(36, 46)),
        (4, "String-Based Logic", range(46, 61)),
        (5, "Arrays and Lists", range(61, 81)),
        (6, "Searching, Sorting and Recursion", range(81, 91)),
        (7, "Interview-Level Logic", range(91, 101)),
    ]
    for number, title, sequence in levels:
        slug = f"logic-level-{number}"
        db.merge(LearningPath(
            slug=slug, title=f"Logic Level {number}: {title}",
            description=f"Guided logic-building practice: {title}. Complete challenges in order.",
            prerequisites=[f"logic-level-{number-1}"] if number > 1 else [],
            status="PUBLISHED", access_scope="ALL",
        ))
        for index, item_number in enumerate(sequence, 1):
            db.merge(LearningPathProblem(
                path_slug=slug, problem_slug=problem_ids[item_number],
                position=index, milestone="Level complete" if index == len(sequence) else None,
            ))
    # One subject knowledge-check path per domain, using the existing access controls.
    for subject in SUBJECTS:
        slugs = subject_questions[subject["slug"]]
        if not slugs:
            continue
        path_slug = "subject-" + subject["slug"][:65]
        db.merge(LearningPath(
            slug=path_slug, title=f'{subject["name"]} — Knowledge Checks',
            description=f'Foundational concept checks in {subject["name"]}; more evaluated exercises are being developed.',
            prerequisites=[], status="PUBLISHED", access_scope="ALL",
        ))
        for position, problem_slug in enumerate(slugs, 1):
            db.merge(LearningPathProblem(
                path_slug=path_slug, problem_slug=problem_slug, position=position,
                milestone="Knowledge check complete" if position == len(slugs) else None,
            ))
    # Series of topic-specific study paths; no extra student-targeting logic.
    for name, title in (("numpy", "NumPy"), ("pandas", "Pandas"),
                        ("data_analysis", "Practical Data Analysis")):
        prior = None
        for level, slugs in sorted(practice_levels[name].items()):
            slug = f"{name.replace('_','-')}-practice-{level}"
            db.merge(LearningPath(
                slug=slug, title=f"{title} — Level {level}",
                description=f"{title} practice with real data, runnable Python and auto-grading.",
                prerequisites=[prior] if prior else [],
                status="PUBLISHED", access_scope="ALL",
            ))
            for position, problem_slug in enumerate(slugs, 1):
                db.merge(LearningPathProblem(
                    path_slug=slug, problem_slug=problem_slug, position=position,
                    milestone="Level complete" if position == len(slugs) else None,
                ))
            prior = slug
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    if db.scalar(select(DailyChallenge).where(DailyChallenge.challenge_date == today)) is None:
        slugs = [entry.slug for entry in entries]
        db.add(DailyChallenge(challenge_date=today, problem_slug=slugs[today.toordinal() % len(slugs)]))
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    contest_slug = f"weekly-{year}-{week}"
    contest = db.scalar(select(Contest).where(Contest.slug == contest_slug))
    if contest is None:
        from datetime import timedelta
        start = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        contest = Contest(slug=contest_slug, title=f"EKLAVYA Weekly {week}", description="A 90-minute algorithm sprint.", starts_at=start, ends_at=start + timedelta(minutes=90))
        db.add(contest); db.flush()
        for position, problem_slug in enumerate(["pair-indices", "first-occurrence", "balanced-delimiters"], 1):
            db.add(ContestProblem(contest_id=contest.id, problem_slug=problem_slug, position=position, points=100))
    db.commit()
    return len(entries)


if __name__ == "__main__":
    with Session() as db:
        print(f"Seeded {seed(db)} problems")
