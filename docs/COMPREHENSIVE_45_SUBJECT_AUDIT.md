# EKLAVYA — 45-Subject Implementation Audit

Updated: 24 November 2026

## Status and scope

The source plan lists 45 minimums totaling **2,500**, although its printed total is **2,560**.
These are different figures; the discrepancy of 60 has not been allocated to a subject.

This PR adds **135 original answer-validated multiple-choice checks** (three per subject),
a browsable 45-subject registry, existing-question mapping, 45 learning paths,
and secure backend subject filters. There are no fabricated practice runtimes.

Before this PR, the seed contained **237** published problems. After it, the
expected seed count is **372**. Of the prior 237, **217** can be directly matched
to this taxonomy: 102 distinct logic problems (including two earlier pattern
problems), 50 NumPy, 50 Pandas and 15 Practical Data Analysis. Another **20
legacy items** remain unclassified in the new taxonomy; these are preserved,
not deleted or relabeled without review.

The table's zero* means **not yet classified**, not necessarily zero existing
content or zero knowledge of the subject.

| ID | Subject | Target | Audited legacy | New | Mapped published | Mapped gap | Execution |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | Programming Foundations and Logic Building | 100 | 102 | 3 | 105 | 0 | Knowledge checks; existing practice |
| 2 | Data Structures and Algorithms | 150 | 0* | 3 | 3 | 147 | Knowledge checks |
| 3 | Object-Oriented Programming | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 4 | SQL and Database Engineering | 120 | 0* | 3 | 3 | 117 | Knowledge checks |
| 5 | NumPy | 50 | 50 | 3 | 53 | 0 | Knowledge checks; existing practice |
| 6 | Pandas | 50 | 50 | 3 | 53 | 0 | Knowledge checks; existing practice |
| 7 | Practical Data Analysis | 50 | 15 | 3 | 18 | 32 | Knowledge checks; existing practice |
| 8 | Data Cleaning and Transformation | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 9 | PySpark | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 10 | Hadoop and MapReduce | 30 | 0* | 3 | 3 | 27 | Knowledge checks |
| 11 | Machine Learning | 100 | 0* | 3 | 3 | 97 | Knowledge checks |
| 12 | Deep Learning | 60 | 0* | 3 | 3 | 57 | Knowledge checks |
| 13 | LLM and Generative AI | 60 | 0* | 3 | 3 | 57 | Knowledge checks |
| 14 | Computer Vision | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 15 | Natural Language Processing | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 16 | Microsoft Excel | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 17 | Tableau | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 18 | Microsoft Power BI and DAX | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 19 | Statistics and Probability | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 20 | Mathematics for AI/ML | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 21 | Linux Commands and Shell Scripting | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 22 | Git and GitHub | 30 | 0* | 3 | 3 | 27 | Knowledge checks |
| 23 | Docker and Containerization | 30 | 0* | 3 | 3 | 27 | Knowledge checks |
| 24 | Kubernetes Fundamentals | 30 | 0* | 3 | 3 | 27 | Knowledge checks |
| 25 | Data Warehousing and ETL | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 26 | Apache Kafka | 40 | 0* | 3 | 3 | 37 | Knowledge checks |
| 27 | Apache Airflow | 40 | 0* | 3 | 3 | 37 | Knowledge checks |
| 28 | REST APIs and Backend Development | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 29 | NoSQL and MongoDB | 40 | 0* | 3 | 3 | 37 | Knowledge checks |
| 30 | Redis and Caching | 30 | 0* | 3 | 3 | 27 | Knowledge checks |
| 31 | Cloud Computing Fundamentals | 40 | 0* | 3 | 3 | 37 | Knowledge checks |
| 32 | MLOps and Model Deployment | 40 | 0* | 3 | 3 | 37 | Knowledge checks |
| 33 | Operating Systems | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 34 | Computer Networks | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 35 | Cybersecurity Fundamentals | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 36 | System Design | 40 | 0* | 3 | 3 | 37 | Knowledge checks |
| 37 | Software Testing and Debugging | 40 | 0* | 3 | 3 | 37 | Knowledge checks |
| 38 | Design Patterns and SOLID Principles | 30 | 0* | 3 | 3 | 27 | Knowledge checks |
| 39 | Quantitative Aptitude | 100 | 0* | 3 | 3 | 97 | Knowledge checks |
| 40 | Logical Reasoning | 100 | 0* | 3 | 3 | 97 | Knowledge checks |
| 41 | English and Verbal Ability | 100 | 0* | 3 | 3 | 97 | Knowledge checks |
| 42 | Web Development | 60 | 0* | 3 | 3 | 57 | Knowledge checks |
| 43 | Business Analytics and Case Studies | 50 | 0* | 3 | 3 | 47 | Knowledge checks |
| 44 | Data Visualization | 40 | 0* | 3 | 3 | 37 | Knowledge checks |
| 45 | AI Agents and Agentic Workflows | 50 | 0* | 3 | 3 | 47 | Knowledge checks |

- Sum of uniquely classified published problems: **352**.
- Unclassified existing legacy problems: **20**.
- Total published seeded problems expected: **372**.
- New question count: **135**, all four-choice MCQs with one private answer
  fixture and a server-side `multiple_choice` evaluator.
- Existing NumPy/Pandas question-bank validators and execution adapters are
  preserved and continue to apply to their earlier code challenges.
- Counted gap is based on *currently classified* content and cannot be
  represented as the audited final gap until the remaining legacy items are mapped.
- No new subjects are falsely described as supporting Excel files, Tableau,
  Power BI, GPU training, Kafka clusters, cloud accounts, or agent execution.
  These first questions for those subjects are concept checks only.

## Architecture

- Catalogue source: `challenges/subject_catalog.json`.
- Subject-specific questions: `challenges/comprehensive_mcq_*.json`.
- Shared assignment, grading and submission logic: existing `Problem`,
  `ProblemEvaluator`, `TestCase`, `LearningPath` and `ALL/SELECTED`.
- Public, audience-aware discovery: `GET /api/v1/subjects`.
- Public list filtering: `GET /api/v1/problems?subject=<slug>`.
- UI: `/subjects`, accessible from the sidebar and linked to real problems.
- User submissions, attempts, access scopes, data lab datasets and API
  authorization rules are preserved.
- No database schema migration is required; entries use existing database
  models and can be seeded through the standard startup workflow.
- Duplicate protection rejects repeated normalized titles and statements
  rather than creating duplicate questions to fill numerical quotas.

## Verification checklist

Run in the repository's normal environment:

```bash
PYTHONPATH=backend pytest -q backend/tests/test_comprehensive_subjects.py
PYTHONPATH=backend pytest -q backend/tests judge/tests
cd frontend
npm run typecheck
npm run build
npm test
```

GitHub Actions performs the integration suite, Docker Compose smoke test,
and isolated NumPy/Pandas reference checks. Only report these as passed
after actual CI completion.

## Remaining work for the full 45-subject expansion

The remaining target requires original vetted questions, assessment fixtures,
appropriate execution environments, optional infrastructure, suitable
workspaces and end-to-end tests. The subject browser is only the catalogue
foundation. It does not mean 2,500 or 2,560 questions are finished.
The plan's acceptance criteria therefore remain **partially complete**.
