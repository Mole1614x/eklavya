# Logic Building — 100-question curriculum

This curriculum expands the existing EKLAVYA catalog without replacing historical
coding, data, SQL, PySpark, AI/ML, Linux, Excel or Tableau challenges.

## Levels

| Level | Questions | Topic | Count |
| --- | --- | --- | --- |
| 1 | 1–15 | Basic Programming | 15 |
| 2 | 16–35 | Number-Based Logic | 20 |
| 3 | 36–45 | Pattern Programming | 10 |
| 4 | 46–60 | String-Based Logic | 15 |
| 5 | 61–80 | Arrays and Lists | 20 |
| 6 | 81–90 | Searching, Sorting and Recursion | 10 |
| 7 | 91–100 | Interview-Level Logic | 10 |

Question 1 reuses `parity-check`, question 17 reuses `sum-of-digits`,
question 91 reuses `pair-indices` (Two Sum), and question 92 reuses
`balanced-delimiters` (Valid Parentheses). These existing problems were
not duplicated or modified, and their previous submissions remain intact.
Ninety-six new problems are loaded from:

- `challenges/logic_levels_1_3.json`
- `challenges/logic_levels_4_5.json`
- `challenges/logic_levels_6_7.json`

Each new problem has a precise input/output contract, a worked example, a
Python starter, and public and hidden judge cases. The included case bank
is introductory, so additional edge-case coverage should be added before
using these questions for high-stakes assessments.

The seed function automatically loads these packs and creates seven
published learning paths `logic-level-1` through `logic-level-7`. All
paths and newly seeded questions use `ALL` access by default and remain
subject to the existing backend access-scope authorization system.

## Activate locally

After pulling the updated branch or merged `main`, run:

```sh
docker compose -p eklavya -f docker-compose.yml -f docker-compose.judge-local.yml --profile judge up -d --build
```

The standard `migrate` service runs `python -m app.seed` and inserts or
updates seed-managed questions. These new questions appear in
`/problems` and their seven paths in `/vidya-paths`.

### Important notes

- The total seeded catalog changes from **26 to 122** entries.
- Existing topic filters and problem slugs continue to work.
- The seed is designed to be rerunnable; no database migration is needed
  because it uses existing Problem, TestCase and LearningPath tables.
- For ordinary learners these are published, available-for-all practice
  challenges. An administrator may subsequently use the access controls to
  target a problem, but rerunning a full seed may reset seed-managed problem
  details (existing behavior). Avoid editing seeded content directly in production;
  use an admin-owned separate slug for customized assignments.
- For judges, whitespace in pattern outputs is significant: do not trim
  leading spaces inside pattern lines. The judge permits an optional trailing newline.

## Tests

```sh
PYTHONPATH=backend pytest -q backend/tests/test_catalog.py backend/tests/test_logic_curriculum.py
cd frontend && npm run typecheck && npm run build && npm test
```
