"""Validate trusted data-practice references in the dedicated NumPy/Pandas runner image.

No user-submitted code is executed here. The references are reviewable source
checked into this repository. This script is a CI-only fixture integrity check.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def normalize(value):
    if isinstance(value, pd.DataFrame):
        return normalize(value.to_dict(orient="records"))
    if isinstance(value, pd.Series):
        return normalize(value.tolist())
    if isinstance(value, np.ndarray):
        return normalize(value.tolist())
    if isinstance(value, np.generic):
        return normalize(value.item())
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def main():
    root = Path(__file__).resolve().parents[1] / "challenges"
    validated = 0
    for pack in ("numpy_practice.json", "pandas_practice.json", "data_analysis_practice.json"):
        records = json.loads((root / pack).read_text(encoding="utf-8"))
        for item in records:
            namespace = {"__name__": f"reference_{item['slug']}"}
            exec(compile(item["reference_source"], item["slug"], "exec"), namespace)
            for test in item["test_inputs"]:
                result = namespace["solve"](test)
                json.dumps(normalize(result), allow_nan=False)
                validated += 1
    assert validated == 230, validated
    print(f"Validated {validated} NumPy/Pandas reference runs")


if __name__ == "__main__":
    main()
