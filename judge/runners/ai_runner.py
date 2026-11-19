import contextlib
import importlib.util
import io
import json

payload = json.loads(open("/source/input.json", encoding="utf-8").read())
config = json.loads(open("/source/config.json", encoding="utf-8").read())
kind = config["kind"]
if kind == "torch_function":
    import torch
else:
    import numpy as np

spec = importlib.util.spec_from_file_location("solution", "/source/solution.py")
module = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(module)
    arguments = []
    for name in config["args"]:
        value = payload[name]
        if name in config.get("array_args", []):
            value = np.asarray(value)
        elif name in config.get("tensor_args", []):
            value = torch.tensor(value, dtype=torch.float32, requires_grad=True)
        arguments.append(value)
    result = getattr(module, config["function"])(*arguments)
if kind == "torch_function":
    if result.shape != arguments[0].shape or result.dtype != arguments[0].dtype:
        raise ValueError("The output tensor must preserve input shape and dtype")
    result = result.detach().cpu().tolist()
elif hasattr(result, "tolist"):
    result = result.tolist()
print("__EKLAVYA_RESULT__" + json.dumps(result, separators=(",", ":")))
