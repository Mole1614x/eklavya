import json
import tempfile
from pathlib import Path

from judge.executor import Execution, run_container

RUNNERS = Path(__file__).parent / "runners"


def execute_sql(source: str, input_data: str) -> Execution:
    return _specialized("python:3.12-alpine", RUNNERS / "sql_runner.py", "solution.sql", source, input_data, {})


def execute_data(kind: str, source: str, input_data: str, config: dict) -> Execution:
    return _specialized("eklavya-data-runner:latest", RUNNERS / "data_runner.py", "solution.py", source, input_data, {"kind": kind, **config})


def execute_bigdata(kind: str, source: str, input_data: str, config: dict) -> Execution:
    image = "python:3.12-alpine" if kind == "mapreduce_function" else "eklavya-bigdata-runner:latest"
    return _specialized(image, RUNNERS / "bigdata_runner.py", "solution.py", source, input_data, {"kind": kind, **config})


def execute_ai(kind: str, source: str, input_data: str, config: dict) -> Execution:
    image = "eklavya-deep-learning-runner:latest" if kind == "torch_function" else "eklavya-ml-runner:latest"
    return _specialized(image, RUNNERS / "ai_runner.py", "solution.py", source, input_data, {"kind": kind, **config})


def evaluate_answer(kind: str, source: str) -> Execution:
    try:
        value = float(source.strip()) if kind == "numerical" else source.strip()
    except ValueError:
        return Execution("WRONG_ANSWER", "The answer is not a valid number.", 0)
    return Execution("COMPLETED", "__EKLAVYA_RESULT__" + json.dumps(value), 0)


def _specialized(image: str, runner: Path, filename: str, source: str, input_data: str, config: dict) -> Execution:
    with tempfile.TemporaryDirectory(prefix="eklavya-specialized-") as directory:
        root = Path(directory)
        (root / filename).write_text(source, encoding="utf-8")
        (root / "runner.py").write_text(runner.read_text(encoding="utf-8"), encoding="utf-8")
        (root / "input.json").write_text(input_data, encoding="utf-8")
        (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
        return run_container(image, root, "exec python /source/runner.py", "")


def extract_result(output: str):
    marker = "__EKLAVYA_RESULT__"
    line = next((line for line in reversed(output.splitlines()) if line.startswith(marker)), None)
    if line is None:
        raise ValueError("Evaluator did not return a result")
    return json.loads(line[len(marker):])


def structured_match(actual, expected, tolerance: float | None = None) -> bool:
    if tolerance is None:
        return actual == expected
    if isinstance(actual, list) and isinstance(expected, list) and len(actual) == len(expected):
        return all(structured_match(left, right, tolerance) for left, right in zip(actual, expected))
    try:
        return abs(float(actual) - float(expected)) <= tolerance
    except (TypeError, ValueError):
        return actual == expected
