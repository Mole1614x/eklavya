# EKLAVYA 45-Subject Question Bank — Expansion Report

## Scope and totals

The authoritative source of subject targets is `challenges/subject_catalog.json`.
All 45 tracks have at least their requested number of published questions
when the database is reseeded from the updated branch.

| Measure | Expected result |
|---|---:|
| Subjects | 45 |
| Sum of subject targets | 2,500 |
| Legacy catalog entries preserved | 372 |
| New conceptual/numerical multiple-choice entries | 2,159 |
| Total catalog after reseeding | **2,531** |
| Classified catalog questions | **2,518** |
| Unclassified legacy catalog questions | **13** |
| Above the summed minimum targets | 18 |

These expected counts are derived from the seeded catalog and subject-classification
rules. The database counts depend on applying the current seed to the database.
Above-target items were retained rather than deleted because learners and submissions
may already reference their stable slugs.

## Content included

The seed loader imports `challenges/comprehensive_mcq_*.json` in sorted file order.
The original 135 subject knowledge checks remain. The added packs are:

| Pack | New questions | Content |
|---|---:|---|
| comprehensive_mcq_04a.json | 170 | Technical domain foundations |
| comprehensive_mcq_04b.json | 250 | Systems, tooling, business and applied concepts |
| comprehensive_mcq_05_calculated.json | 601 | DSA, SQL query semantics, ML metrics, aptitude, reasoning, statistics and applied analytics |
| comprehensive_mcq_06a.json | 128 | OOP, data cleaning, PySpark and Hadoop |
| comprehensive_mcq_06b.json | 168 | Deep learning, LLMs, computer vision and NLP |
| comprehensive_mcq_06c.json | 236 | Excel, Tableau, DAX, Linux, Git, Docker, Kubernetes and ETL |
| comprehensive_mcq_06d.json | 189 | Kafka, Airflow, REST APIs, MongoDB, Redis, cloud and MLOps |
| comprehensive_mcq_06e.json | 182 | Operating systems, networking, cybersecurity, system design and testing |
| comprehensive_mcq_06f.json | 148 | Web development, business analytics, visualization and agents |
| comprehensive_mcq_06g_english.json | 87 | English grammar, spelling, vocabulary and phrasal verbs |
| **Total** | **2,159** | **All under-target subjects expanded** |

The existing seed system assigns deterministic `knowledge-...` slugs, shuffles
option positions, stores expected answers in hidden grading cases and enrolls
questions in subject learning paths. The published problem payload does not
expose hidden expected-answer fixtures.

## Verification and content limitations

Checks on all 2,294 subject MCQs (135 original plus 2,159 new) found no duplicated
normalized subject/skill title, no duplicated normalized prompt statement, and no
invalid four-option answer sets. The seed-time duplicate check uses indexed lookups
to avoid quadratic work at this scale. CI tests and real database reseeding remain
the ultimate acceptance criteria; do not infer successful execution from the JSON
checks alone.

**Format limitation:** The 2,159 new entries are MCQs, not 2,159 executable
coding solutions. The existing programming, data-processing and other specialized
judge exercises remain intact. Future curriculum work should add independently
executable Python/Java/C/C++/SQL/Pandas/PySpark examples and deeper Excel/Tableau
practice where supported by a verified evaluator. Concept checks should not be
presented as equivalent to runnable engineering exercises.

**Explanations:** New conceptual items have a verified answer, but the existing
public MCQ schema does not currently expose per-option instructional explanations.
Explanations should be added as a separate reviewed capability instead of
embedding grading secrets in a public payload.

## Apply and inspect

Use the normal migration-and-seed workflow on the updated branch.

```bash
cd backend
alembic upgrade head
python -m app.seed
```

For a running local API, verify both endpoints:

```bash
curl -s "http://localhost:8001/api/v1/problems?limit=1" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["total"])'
curl -s "http://localhost:8001/api/v1/subjects" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["published_catalog_total"], d["classified_published"])'
```

Run the backend and judge unit tests plus the database migration checks before
merging or deploying. A seeded local or test database is required to independently
confirm the exact counts; the user's currently running local database is not
accessible from this branch.
