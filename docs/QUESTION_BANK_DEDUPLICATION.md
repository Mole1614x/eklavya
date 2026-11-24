# Question bank uniqueness and expansion policy

## Scope and baseline (24 November 2026)

The 45 subject targets in the uploaded EKLAVYA comprehensive expansion plan
sum to **2,500**, not the stated 2,560. The requested extra 60 questions
have not been assigned to a subject; do not silently make them up.

The pre-expansion seed catalog contains **237 records**, including 100
numbered logic curriculum slots, 50 NumPy exercises, 50 Pandas exercises and
15 data-analysis exercises. These counts represent seed entries, **not** proof
that all new subject targets have been completed. A full subject-by-subject
gap audit and validated content expansion remain separate work.

## Deduplication rules

1. Treat **an existing problem slug as canonical** for that same learning
   objective; learning tracks should reference it instead of cloning its
   problem and tests. An exercise may belong to multiple paths.
2. For new content, reject same normalized title within the same execution
   family and question format. Ignore cosmetic punctuation, capitalization,
   or extra whitespace.
3. Also reject **identical** normalized descriptions within the same execution
   family and format. Similar statements with different numbers or operations
   must remain distinct. Different technologies (e.g. raw Python vs NumPy vs
   Pandas) are allowed to have legitimately different programming tasks.
4. Before creating a question in Content Studio, inspect
   `GET /api/v1/admin/problems/duplicate-check` using `title`, `category`,
   `format`, optional `topic`, `description` and `exclude_slug`.
   The endpoint requires administrator access and returns matching canonical
   slugs and conflict reasons.
5. If duplicate creation is attempted through the admin write endpoint, the
   API returns **409** with the existing slug/title. Edit the existing question
   in place, attach it to an additional learning path, or replace the proposed
   question with a substantively different objective.
6. New seed packs are checked *before* database writes. An unseen duplicate
   raises a descriptive error; regenerate that pack entry with a novel task
   and validated tests instead of artificially inflating the catalog count.
7. **Never rewrite an already-published problem's input/output contract**
   merely to make the counts appear unique. Prior submissions, results,
   assignments and lesson progress rely on stable slugs and semantics.
   Administrative updates to a canonical question remain permitted.
8. Existing legacy semantic overlap: `first-occurrence` and
   `binary-search-index` both teach finding the first occurrence of a
   target in a sorted array. Both remain addressable to avoid breaking
   historical URLs, submissions, or assessments. Future curricula should
   link to one canonical record for that objective. The legacy exception
   applies only to this named pair, never to newly created duplicates.

## Limitations

The detector is deliberately conservative. It catches exact normalized
titles, identical normalized statements, and one verified legacy equivalence. It
**does not claim** to infer all semantic equivalences or guarantee a
duplicate-free 2,500+ catalog. Future imports require a human-reviewed
similarity report and validated reference results, especially when identical
objectives have significantly different wording.

The complete 45-subject platform expansion (new runtimes, 2,500+ content,
UI workspaces and assessment integrations) is **not implemented** by this
deduplication change. Unsupported subjects must not be marked completed.

## Verification

```sh
PYTHONPATH=backend pytest -q \
  backend/tests/test_problem_uniqueness.py \
  backend/tests/test_admin.py \
  backend/tests/test_catalog.py
```

Also run the full backend, judge, frontend and Docker smoke suites before merge.
