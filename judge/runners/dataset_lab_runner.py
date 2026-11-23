import contextlib
import io
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

config = json.loads(Path("/source/config.json").read_text(encoding="utf-8"))
source = Path("/source/solution.txt").read_text(encoding="utf-8")
dataset = Path("/source/dataset" + config["extension"])
dataset_format = config["format"]

if dataset_format == "CSV":
    df = pd.read_csv(dataset)
elif dataset_format == "JSON":
    df = pd.read_json(dataset)
elif dataset_format == "XLSX":
    df = pd.read_excel(dataset)
elif dataset_format == "PARQUET":
    import duckdb
    df = duckdb.connect(":memory:").read_parquet(str(dataset)).df()
else:
    raise ValueError("Unsupported dataset format")

if len(df) > 10_000 or len(df.columns) > 200:
    raise ValueError("Dataset exceeds the practice sandbox limit")

captured = io.StringIO()
with contextlib.redirect_stdout(captured):
    if config["technology"] == "SQL":
        connection = sqlite3.connect(":memory:")
        try:
            df.to_sql("dataset", connection, index=False)
            result = pd.read_sql_query(source, connection)
        finally:
            connection.close()
    else:
        namespace = {"df": df.copy(), "np": np, "pd": pd}
        exec(compile(source, "solution.py", "exec"), {"__builtins__": __builtins__}, namespace)
        result = namespace.get("result")
        if result is None and captured.getvalue():
            result = captured.getvalue().rstrip()

if isinstance(result, pd.DataFrame):
    value = json.loads(result.head(1000).to_json(orient="split", date_format="iso"))
elif isinstance(result, pd.Series):
    value = result.head(1000).tolist()
elif isinstance(result, np.ndarray):
    value = result.tolist()
elif isinstance(result, np.generic):
    value = result.item()
elif isinstance(result, (str, int, float, bool, list, dict)) or result is None:
    value = result
else:
    value = repr(result)
print("__EKLAVYA_RESULT__" + json.dumps(value, default=str, separators=(",", ":")))
