import json
import tempfile
import time
import shutil
from pathlib import Path, PurePosixPath

from backend.app.advanced_evaluators import ExpressionError, evaluate_excel, evaluate_tableau
from judge.executor import Execution, run_container

RUNNERS = Path(__file__).parent / "runners"


def evaluate_expression(kind: str, source: str, input_data: str) -> Execution:
    started = time.monotonic()
    try:
        fixture = json.loads(input_data)
        if kind == "excel_formula":
            result = evaluate_excel(source, fixture.get("cells", {}))
        elif kind == "tableau_expression":
            result = evaluate_tableau(source, fixture.get("rows", []), fixture.get("fields") or None,
                                      fixture.get("partition_by"), fixture.get("order_by"))
        else:
            return Execution("UNSUPPORTED_EVALUATOR", "Expression evaluator is unavailable.", 0)
        return Execution("COMPLETED", "__EKLAVYA_RESULT__" + json.dumps(result), int((time.monotonic() - started) * 1000))
    except (ExpressionError, json.JSONDecodeError, TypeError) as error:
        return Execution("WRONG_ANSWER", str(error), int((time.monotonic() - started) * 1000))


def execute_bash(source: str, input_data: str) -> Execution:
    try:
        fixture = json.loads(input_data or "{}")
        files = fixture.get("files", {})
        stdin = str(fixture.get("stdin", ""))
        if not isinstance(files, dict) or len(files) > 100:
            raise ValueError("Invalid shell fixture")
        with tempfile.TemporaryDirectory(prefix="eklavya-bash-") as directory:
            root = Path(directory)
            (root / "solution.sh").write_text(source, encoding="utf-8")
            fixture_root = root / "fixture"
            fixture_root.mkdir()
            for name, content in files.items():
                relative = PurePosixPath(str(name))
                if relative.is_absolute() or ".." in relative.parts or len(str(content)) > 100_000:
                    raise ValueError("Invalid shell fixture path or content")
                target = fixture_root.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(content), encoding="utf-8")
            return run_container("alpine:3.21", root, "cp -R /source/fixture/. /work/ && exec /bin/sh /source/solution.sh", stdin)
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as error:
        return Execution("SYSTEM_ERROR", str(error), 0)


def execute_dataset_practice(technology: str, source: str, dataset_path: Path, dataset_format: str) -> Execution:
    extension = {"CSV": ".csv", "JSON": ".json", "XLSX": ".xlsx", "PARQUET": ".parquet"}.get(dataset_format)
    if extension is None:
        return Execution("SYSTEM_ERROR", "Dataset format is unsupported by the practice sandbox.", 0)
    try:
        with tempfile.TemporaryDirectory(prefix="eklavya-data-lab-") as directory:
            root = Path(directory)
            shutil.copyfile(dataset_path, root / f"dataset{extension}")
            (root / "solution.txt").write_text(source, encoding="utf-8")
            (root / "runner.py").write_text((RUNNERS / "dataset_lab_runner.py").read_text(encoding="utf-8"), encoding="utf-8")
            (root / "config.json").write_text(json.dumps({"technology": technology, "format": dataset_format, "extension": extension}), encoding="utf-8")
            return run_container("eklavya-data-runner:latest", root, "exec python /source/runner.py", "")
    except OSError as error:
        return Execution("SYSTEM_ERROR", str(error), 0)
