# EKLAVYA — 45-Subject Question Bank Coverage Audit

Updated: 24 November 2026

## Audited completion of subject question counts

The original request's **45 minimums sum to 2,500**, although a headline
in the source document says 2,560. This release satisfies **every one of
the 45 individual minima** and therefore the mathematically grounded
2,500-question target. It does not claim to have allocated the discrepancy
of 60 to additional subjects.

**Before this change:** 372 published seed questions, including 135 original
MCQs and 237 earlier practice exercises.

**This change:** 2,155 new, separately authored conceptual multiple-choice
questions about distinct topics and skills. The corpus is additive and
preserves the 372 existing problem slugs, submissions and assessment results.

**After this change:**
- **2,527** total seeded questions
- **2,514** mapped to the 45-subject taxonomy (14 above minimums because
  Programming, NumPy and Pandas were already over target)
- **13** earlier questions retained without a new subject taxonomy assignment
- **2,290** MCQs in the subject tracks (135 prior + 2,155 new)
- **Zero** missing questions against any of the 45 individual minimums

## Complete per-subject tally

| # | Subject | Minimum | Before | New | After |
|---:|---|---:|---:|---:|---:|
| 1 | Programming Foundations and Logic Building | 100 | 105 | 0 | **105** |
| 2 | Data Structures and Algorithms | 150 | 3 | 147 | **150** |
| 3 | Object-Oriented Programming | 50 | 3 | 47 | **50** |
| 4 | SQL and Database Engineering | 120 | 3 | 117 | **120** |
| 5 | NumPy | 50 | 54 | 0 | **54** |
| 6 | Pandas | 50 | 55 | 0 | **55** |
| 7 | Practical Data Analysis | 50 | 18 | 32 | **50** |
| 8 | Data Cleaning and Transformation | 50 | 3 | 47 | **50** |
| 9 | PySpark | 50 | 4 | 46 | **50** |
| 10 | Hadoop and MapReduce | 30 | 3 | 27 | **30** |
| 11 | Machine Learning | 100 | 5 | 95 | **100** |
| 12 | Deep Learning | 60 | 4 | 56 | **60** |
| 13 | LLM and Generative AI | 60 | 3 | 57 | **60** |
| 14 | Computer Vision | 50 | 3 | 47 | **50** |
| 15 | Natural Language Processing | 50 | 3 | 47 | **50** |
| 16 | Microsoft Excel | 50 | 3 | 47 | **50** |
| 17 | Tableau | 50 | 3 | 47 | **50** |
| 18 | Microsoft Power BI and DAX | 50 | 3 | 47 | **50** |
| 19 | Statistics and Probability | 50 | 3 | 47 | **50** |
| 20 | Mathematics for AI/ML | 50 | 3 | 47 | **50** |
| 21 | Linux Commands and Shell Scripting | 50 | 3 | 47 | **50** |
| 22 | Git and GitHub | 30 | 3 | 27 | **30** |
| 23 | Docker and Containerization | 30 | 3 | 27 | **30** |
| 24 | Kubernetes Fundamentals | 30 | 3 | 27 | **30** |
| 25 | Data Warehousing and ETL | 50 | 3 | 47 | **50** |
| 26 | Apache Kafka | 40 | 3 | 37 | **40** |
| 27 | Apache Airflow | 40 | 3 | 37 | **40** |
| 28 | REST APIs and Backend Development | 50 | 3 | 47 | **50** |
| 29 | NoSQL and MongoDB | 40 | 3 | 37 | **40** |
| 30 | Redis and Caching | 30 | 3 | 27 | **30** |
| 31 | Cloud Computing Fundamentals | 40 | 3 | 37 | **40** |
| 32 | MLOps and Model Deployment | 40 | 3 | 37 | **40** |
| 33 | Operating Systems | 50 | 3 | 47 | **50** |
| 34 | Computer Networks | 50 | 3 | 47 | **50** |
| 35 | Cybersecurity Fundamentals | 50 | 3 | 47 | **50** |
| 36 | System Design | 40 | 3 | 37 | **40** |
| 37 | Software Testing and Debugging | 40 | 3 | 37 | **40** |
| 38 | Design Patterns and SOLID Principles | 30 | 3 | 27 | **30** |
| 39 | Quantitative Aptitude | 100 | 3 | 97 | **100** |
| 40 | Logical Reasoning | 100 | 3 | 97 | **100** |
| 41 | English and Verbal Ability | 100 | 3 | 97 | **100** |
| 42 | Web Development | 60 | 3 | 57 | **60** |
| 43 | Business Analytics and Case Studies | 50 | 3 | 47 | **50** |
| 44 | Data Visualization | 40 | 3 | 37 | **40** |
| 45 | AI Agents and Agentic Workflows | 50 | 3 | 47 | **50** |

The counts refer to questions available through the existing published
Problem system, under the normal audience and publication controls.
They do not measure how well a student has mastered the subjects.

## Scope of this completion

- The new questions are **concept checks**, each measuring a named distinct
  concept and containing four unique statements from the *same subject*.
- One answer is selected and verified against a private answer-key test case
  by the existing `multiple_choice` evaluator. Distractors and answer-order
  variation are deterministic and checked during seeding.
- Questions are organized into each subject's existing published learning
  path and are accessible from `/subjects` and `/problems`.
- Duplicated subject names and normalized questions are rejected before any
  database write; the pre-seed audit also checks overlap with the prior 135
  knowledge checks and verifies all 45 subject minima.
- The original 100-step Logic curriculum, 50 NumPy and 50 Pandas code exercises,
  and 15 practical data-analysis code challenges are preserved and counted
  where applicable, rather than copied into new slugs.
- The earlier `first-occurrence` / `binary-search-index` legacy equivalence
  remains addressable to preserve prior learner submissions and URLs.

## Important boundary: subject questions versus special environments

**Completing the numerical question-bank target does not imply that every
requested subject has a custom interactive runtime.** The 2,155 new entries
are conceptual MCQs; they are not 2,155 tested coding programs, spreadsheets,
Power BI projects, cloud deployments or production agent environments.
Existing supported CODE, SQL, Data Lab and language runtimes are not changed.
The full specialized-practice infrastructure in the original product plan
is separate work and must not be marked complete solely on question count.

## Audit and verification

```sh
python scripts/verify_subject_concepts.py
PYTHONPATH=backend pytest -q backend/tests/test_comprehensive_subjects.py
```

Run the full GitHub Actions CI (backend/judge tests, frontend build,
browser tests, database migrations, Docker smoke tests and NumPy/Pandas
reference execution) before treating the branch as production ready.
