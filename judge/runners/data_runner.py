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
with contextlib.redirect_stdout(io.StringIO()):
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
print("__EKLAVYA_RESULT__" + json.dumps(result, separators=(",", ":")))
