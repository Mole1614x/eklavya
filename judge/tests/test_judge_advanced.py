import json

from judge.advanced import evaluate_expression, execute_bash, execute_dataset_practice
from judge.executor import Execution, container_command


def test_excel_and_tableau_evaluators_use_supported_semantics():
    excel = evaluate_expression("excel_formula", "=SUMIF(A2:A4,E2,B2:B4)", json.dumps({
        "cells": {"A2": "West", "A3": "East", "A4": "West", "B2": 5, "B3": 8, "B4": 7, "E2": "West"},
    }))
    assert excel.verdict == "COMPLETED" and excel.output.endswith("12.0")
    malicious = evaluate_expression("excel_formula", '=__import__("os")', "{}")
    assert malicious.verdict == "WRONG_ANSWER"
    tableau = evaluate_expression("tableau_expression", "SUM([Profit]) / SUM([Sales])", json.dumps({
        "rows": [{"Profit": 20, "Sales": 100}, {"Profit": 30, "Sales": 150}],
    }))
    assert tableau.verdict == "COMPLETED" and tableau.output.endswith("0.2")


def test_bash_container_is_unprivileged_and_rejects_fixture_traversal(tmp_path):
    command = container_command("bash", tmp_path, "submission")
    assert command[command.index("--user") + 1] == "65534:65534"
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert "no-new-privileges" in command
    rejected = execute_bash("echo test", '{"files":{"../secret":"bad"}}')
    assert rejected.verdict == "SYSTEM_ERROR"


def test_dataset_practice_is_delegated_to_data_runner(monkeypatch, tmp_path):
    dataset = tmp_path / "data.csv"; dataset.write_text("region,sales\nWest,5\n", encoding="utf-8")
    captured = {}
    def fake_run(image, source_directory, command, input_data):
        captured.update({"image": image, "files": sorted(path.name for path in source_directory.iterdir()), "command": command, "input": input_data})
        return Execution("COMPLETED", "__EKLAVYA_RESULT__[]", 1)
    monkeypatch.setattr("judge.advanced.run_container", fake_run)
    result = execute_dataset_practice("PANDAS", "result = df", dataset, "CSV")
    assert result.verdict == "COMPLETED"
    assert captured == {"image": "eklavya-data-runner:latest", "files": ["config.json", "dataset.csv", "runner.py", "solution.txt"], "command": "exec python /source/runner.py", "input": ""}
