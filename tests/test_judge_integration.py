"""Opt-in end-to-end judge tests. Run only in trusted local Docker Desktop.

EKLAVYA_JUDGE_INTEGRATION=1 pytest -q tests/test_judge_integration.py
"""
import json
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("EKLAVYA_JUDGE_INTEGRATION") != "1",
    reason="Requires trusted local Docker Desktop and all judge runner images",
)

from judge.executor import execute, outputs_match
from judge.specialized import (
    execute_sql, execute_data, execute_bigdata, execute_ai, extract_result,
)
from judge.advanced import execute_bash


@pytest.mark.parametrize("language,source", [
    ("python", "print(4)"),
    ("java", "public class Main { public static void main(String[] args) { System.out.println(4); } }"),
    ("c", '#include <stdio.h>\nint main(){puts("4");return 0;}'),
    ("cpp", '#include <iostream>\nint main(){std::cout << 4 << std::endl;}'),
    ("bash", "echo 4"),
])
def test_languages(language, source):
    result = execute(language, source, "")
    assert (result.verdict, result.output.strip()) == ("COMPLETED", "4")


def test_runtime_error():
    assert execute("python", "raise RuntimeError('test')", "").verdict == "RUNTIME_ERROR"


def test_compile_error():
    assert execute("c", "int main( {", "").verdict == "COMPILATION_ERROR"


def test_stdin_and_wrong_answer_comparison():
    result = execute("python", "a,b=map(int,input().split());print(a+b)", "10 20\n")
    assert result.verdict == "COMPLETED" and outputs_match(result.output, "30")
    assert not outputs_match(result.output, "31")


def test_sql():
    fixture = {"tables": {"t": {"columns": [["id", "INTEGER"]],
                               "rows": [[1], [2]]}}}
    result = execute_sql("SELECT SUM(id) AS total FROM t", json.dumps(fixture))
    assert result.verdict == "COMPLETED", result.output
    assert extract_result(result.output)["rows"] == [[3]]


def test_linux_fixture():
    result = execute_bash("cat hello.txt", json.dumps(
        {"files": {"hello.txt": "EKLAVYA"}, "stdin": ""}))
    assert (result.verdict, result.output.strip()) == ("COMPLETED", "EKLAVYA")


def test_numpy():
    result = execute_data("numpy_expression", "arr * 2",
                          json.dumps({"array": [1, 2, 3]}),
                          {"variable": "arr", "output": "array"})
    assert result.verdict == "COMPLETED", result.output
    assert extract_result(result.output) == [2, 4, 6]


def test_mapreduce():
    source = (
        "def mapper(line):\n"
        "    return [(word, 1) for word in line.split()]\n"
        "def reducer(key, values):\n"
        "    return key, sum(values)\n"
    )
    config = {"map_function": "mapper", "reduce_function": "reducer"}
    result = execute_bigdata("mapreduce_function", source,
                             json.dumps({"lines": ["a b", "a"]}), config)
    assert result.verdict == "COMPLETED", result.output
    assert extract_result(result.output) == [["a", 2], ["b", 1]]


def test_ai_numpy():
    source = "def double(x):\n    return x * 2\n"
    config = {"args": ["x"], "array_args": ["x"], "function": "double"}
    result = execute_ai("numpy_ai_function", source, json.dumps({"x": [1, 2]}), config)
    assert result.verdict == "COMPLETED", result.output
    assert extract_result(result.output) == [2, 4]


def test_time_limit():
    result = execute("python", "while True: pass", "")
    assert result.verdict == "TIME_LIMIT_EXCEEDED", result


def test_output_limit():
    result = execute("python", "while True: print('X' * 2000, flush=True)", "")
    assert result.verdict == "OUTPUT_LIMIT_EXCEEDED", result
