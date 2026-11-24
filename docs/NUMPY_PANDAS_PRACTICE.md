# NumPy, Pandas and Practical Data Analysis — 115 Exercises

This curriculum follows the uploaded practice sheet's order:

| Track | Levels | Number of exercises | EKLAVYA topic |
| --- | --- | ---: | --- |
| NumPy | Fundamentals; Indexing; Mathematics; Matrix operations; Advanced NumPy | 50 | Data → NumPy · Level 1–5 |
| Pandas | Fundamentals; Filtering; Cleaning; GroupBy; Advanced Pandas | 50 | Data → Pandas · Level 1–5 |
| Practical Data Analysis | Sales/customer analytics; data preparation; end-to-end analysis | 15 | Data → Practical Data Analysis · Level 1–3 |

The original 10-row employee fixture (Amit, Neha, Rahul, Priya, Ravi,
Sneha, Karan, Pooja, Arjun, and Simran) is included in the Pandas problems.
Age and Salary null values are represented as JSON `null`.

Each question defines a deterministic `solve(data)` contract. Examples from
the original list have been clarified into actual return-value contracts,
with tie-handling, missing-data behavior and sort ordering where relevant.

### Running a solution

Open the challenge in the **Data** topic, select Python, and implement:

```python
import numpy as np
import pandas as pd

def solve(data):
    # data is the JSON-decoded input for this problem
    return ...
```

No `input()` or `print()` is needed; return a JSON-compatible value.
NumPy arrays, Pandas Series and DataFrames can also be returned and are
normalized before comparison. Two deterministic fixtures are configured for
each challenge; the second case is hidden.

Unlike the standard Python runner, these exercises run in EKLAVYA's
existing isolated `eklavya-data-runner` image with NumPy, Pandas and
OpenPyXL installed. The platform uses a **separate isolated execution** for
the trusted reference implementation. Learner source cannot access the
reference source through its runner configuration. The student's result
is compared to the reference with numerical tolerance.

### Scope and limitations

- The questions are published for `ALL` eligible students and participate
  in the existing student-access permissions, progress, and completion
  tracking.
- Three families of learning paths are available: `numpy-practice-1..5`,
  `pandas-practice-1..5`, and `data-analysis-practice-1..3`.
- Some source questions were open-ended, so the programmatic version fixes
  reasonable definitions. In particular, the Excel-reading exercise uses
  an **in-memory generated XLSX worksheet**, because assessment execution
  does not expose arbitrary host files.
- The random-integers question uses a supplied seed to make grading
  reproducible.
- **Public worked answers are not included yet**. The two test inputs are
  real grading fixtures and are validated by the reference runner, but
  expected values are computed at grading time. This is suitable for
  practice, not as a complete teaching-answer workbook.
- Content is additive; no existing SQL, PySpark, Linux, logic, or assessment
  records are deleted.

### Source and verification

Source data is in `challenges/numpy_practice.json`,
`challenges/pandas_practice.json`, and
`challenges/data_analysis_practice.json`.

Run:

```sh
PYTHONPATH=backend pytest -q backend/tests/test_data_practice_curriculum.py
docker build -f judge/images/data.Dockerfile -t eklavya-data-runner:latest .
docker run --rm --network none --read-only --cap-drop ALL \
  -v "$PWD/challenges:/work/challenges:ro" \
  -v "$PWD/scripts:/work/scripts:ro" \
  -w /work eklavya-data-runner:latest \
  python scripts/verify_data_practice_references.py
```

The second check executes 230 trusted reference test inputs using the
same library versions as the real restricted data runner.

After merging, rebuild with the judge profile so the new question bank
and evaluator are active.
