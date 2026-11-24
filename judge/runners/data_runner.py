import contextlib
import importlib.util
import io
import json

import numpy as np
import pandas as pd

payload = json.loads(open("/source/input.json", encoding="utf-8").read())
config = json.loads(open("/source/config.json", encoding="utf-8").read())
source = open("/source/solution.py", encoding="utf-8").read()
kind = config["kind"]
def normalize(value):
    """Convert supported NumPy/Pandas types to strict, JSON-safe values."""
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
    if value is None:
        return None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is pd.NA or value is pd.NaT:
        return None
    return value


with contextlib.redirect_stdout(io.StringIO()):
    if kind == "data_practice_function":
        spec = importlib.util.spec_from_file_location("solution", "/source/solution.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = getattr(module, config.get("function", "solve"))(payload)
        print_result = normalize(result)
    else:
        value = pd.DataFrame(payload["dataframe"]) if kind.startswith("pandas") else np.array(payload["array"])
        if kind.endswith("expression"):
            namespace = {config["variable"]: value, "pd": pd, "np": np}
            result = eval(compile(source, "solution.py", "eval"), {"__builtins__": __builtins__}, namespace)
        else:
            spec = importlib.util.spec_from_file_location("solution", "/source/solution.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            result = getattr(module, config["function"])(value)
        if config["output"] == "dataframe_split":
            result = json.loads(result.to_json(orient="split", date_format="iso"))
        elif config["output"] == "array":
            result = np.asarray(result).tolist()
        print_result = result
print("__EKLAVYA_RESULT__" + json.dumps(print_result, separators=(",", ":"), allow_nan=False))
