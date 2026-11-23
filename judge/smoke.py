"""Smoke-test the local EKLAVYA Docker judge without pytest.

Run inside the trusted local judge container:
    python -m judge.smoke
"""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from judge.executor import execute, outputs_match
from judge.specialized import execute_sql, execute_data, execute_bigdata, execute_ai, extract_result
from judge.advanced import execute_bash, execute_dataset_practice


def run() -> int:
    failures = []

    def check(name, action):
        try:
            result = action()
            if result is False:
                raise AssertionError("returned false")
            print(f"PASS | {name}", flush=True)
        except Exception as error:
            failures.append(name)
            print(f"FAIL | {name} | {type(error).__name__}: {error}", flush=True)

    languages = {
        "python": "print(4)",
        "java": "public class Main { public static void main(String[] args) { System.out.println(4); }}",
        "c": '#include <stdio.h>\nint main(){puts("4");return 0;}',
        "cpp": '#include <iostream>\nint main(){std::cout << 4 << std::endl;}',
        "bash": "echo 4",
    }

    def expect(language, source, stdin, verdict, output=None):
        result = execute(language, source, stdin)
        assert result.verdict == verdict, result
        if output is not None:
            assert result.output.strip() == output, result
        return True

    for language, source in languages.items():
        check(f"language {language}", lambda l=language, s=source: expect(l, s, "", "COMPLETED", "4"))

    check("python stdin", lambda: expect("python", "a,b=map(int,input().split());print(a+b)", "10 20\n", "COMPLETED", "30"))
    check("runtime error", lambda: expect("python", "raise RuntimeError()", "", "RUNTIME_ERROR"))
    check("C compilation error", lambda: expect("c", "int main( {", "", "COMPILATION_ERROR"))
    check("Java compilation error", lambda: expect("java", "public class Main { invalid }", "", "COMPILATION_ERROR"))
    check("unsupported language", lambda: expect("ruby", "puts 1", "", "UNSUPPORTED_LANGUAGE"))
    check("wrong answer comparison", lambda: not outputs_match("25\n", "30"))
    check("zero tolerance", lambda: not outputs_match("3.00001", "3", 0.0))

    def sql_check():
        fixture = {"tables": {"t": {"columns": [["id", "INTEGER"]], "rows": [[1], [2]]}}}
        result = execute_sql("SELECT SUM(id) AS total FROM t", json.dumps(fixture))
        assert result.verdict == "COMPLETED", result
        return extract_result(result.output)["rows"] == [[3]]
    check("SQL", sql_check)

    def linux_check():
        result = execute_bash("cat hello.txt", json.dumps({"files": {"hello.txt": "EKLAVYA"}, "stdin": ""}))
        assert result.verdict == "COMPLETED", result
        return result.output.strip() == "EKLAVYA"
    check("Linux fixture", linux_check)

    def numpy_check():
        result = execute_data("numpy_expression", "arr * 2",
                              json.dumps({"array": [1, 2, 3]}),
                              {"variable": "arr", "output": "array"})
        assert result.verdict == "COMPLETED", result
        return extract_result(result.output) == [2, 4, 6]
    check("NumPy", numpy_check)

    def mapreduce_check():
        source = "def mapper(line):\n    return [(w, 1) for w in line.split()]\ndef reducer(k, values):\n    return k, sum(values)\n"
        result = execute_bigdata("mapreduce_function", source,
            json.dumps({"lines": ["a b", "a"]}),
            {"map_function": "mapper", "reduce_function": "reducer"})
        assert result.verdict == "COMPLETED", result
        return extract_result(result.output) == [["a", 2], ["b", 1]]
    check("MapReduce", mapreduce_check)

    def ai_check():
        result = execute_ai("numpy_ai_function", "def double(x):\n    return x * 2\n",
            json.dumps({"x": [1, 2]}),
            {"args": ["x"], "array_args": ["x"], "function": "double"})
        assert result.verdict == "COMPLETED", result
        return extract_result(result.output) == [2, 4]
    check("AI NumPy function", ai_check)

    def data_lab_check():
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.csv"
            path.write_text("value\n2\n3\n", encoding="utf-8")
            result = execute_dataset_practice(
                "PANDAS", "result = int(df['value'].sum())", path, "CSV")
            assert result.verdict == "COMPLETED", result
            return extract_result(result.output) == 5
    check("Dataset CSV", data_lab_check)

    check("time limit", lambda: expect("python", "while True: pass", "", "TIME_LIMIT_EXCEEDED"))
    check("output limit", lambda: expect("python", "while True: print('X'*2000, flush=True)", "", "OUTPUT_LIMIT_EXCEEDED"))

    print(f"RESULT | {len(failures)} failed", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
