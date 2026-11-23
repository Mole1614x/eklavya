import os
import selectors
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

MAX_OUTPUT_BYTES = 64 * 1024
TIME_LIMIT_SECONDS = 5
CONTAINER_OVERHEAD_SECONDS = 2


@dataclass(frozen=True)
class Execution:
    verdict: str
    output: str
    execution_ms: int
    memory_kb: int | None = None


LANGUAGES = {
    "python": ("python:3.12-alpine", "main.py", "exec python /source/main.py"),
    "c": ("eklavya-code-runner:latest", "Main.c", "gcc -O2 -std=c17 /source/Main.c -o /work/main || { echo Compilation failed >&2; exit 90; }; exec /work/main"),
    "cpp": ("eklavya-code-runner:latest", "Main.cpp", "g++ -O2 -std=c++20 /source/Main.cpp -o /work/main || { echo Compilation failed >&2; exit 90; }; exec /work/main"),
    "java": ("eclipse-temurin:21-jdk-alpine", "Main.java", "cp /source/Main.java /work/Main.java && javac /work/Main.java || { echo Compilation failed >&2; exit 90; }; exec java -cp /work Main"),
    "bash": ("alpine:3.21", "main.sh", "exec /bin/sh /source/main.sh"),
}


def container_command(language: str, source_directory: Path, name: str) -> list[str]:
    try:
        image, _, command = LANGUAGES[language]
    except KeyError as error:
        raise ValueError(f"Unsupported language: {language}") from error
    return isolated_command(image, source_directory, name, command)


def isolated_command(image: str, source_directory: Path, name: str, command: str) -> list[str]:
    return [
        "docker", "run", "--rm", "--interactive", "--name", name,
        "--pull", "never",
        "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--user", "65534:65534",
        "--security-opt", "no-new-privileges", "--pids-limit", "64",
        "--memory", "256m", "--memory-swap", "256m", "--cpus", "0.5",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m,mode=1777",
        "--tmpfs", "/work:rw,exec,nosuid,size=64m,mode=1777",
        "--volume", f"{source_directory}:/source:ro", "--workdir", "/work",
        image, "sh", "-c", command,
    ]


def execute(language: str, source_code: str, input_data: str) -> Execution:
    if language not in LANGUAGES:
        return Execution("UNSUPPORTED_LANGUAGE", "This language is unavailable in the judge.", 0)
    _, filename, _ = LANGUAGES[language]
    with tempfile.TemporaryDirectory(prefix="eklavya-judge-") as directory:
        source_directory = Path(directory)
        (source_directory / filename).write_text(source_code, encoding="utf-8")
        image, _, command = LANGUAGES[language]
        return run_container(image, source_directory, command, input_data)


def run_container(image: str, source_directory: Path, command: str, input_data: str) -> Execution:
        _prepare_source_directory(source_directory)
        name = f"eklavya-{uuid4().hex}"
        started = time.monotonic()
        process = subprocess.Popen(
            isolated_command(image, source_directory, name, command), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(input_data.encode())
        process.stdin.close()
        os.set_blocking(process.stdout.fileno(), False)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        output = bytearray()
        # Container creation, JVM startup, and scientific-library imports are
        # platform overhead rather than user work. Keep that allowance bounded.
        # Container creation, JVM startup, and scientific-library imports are
        # platform overhead rather than user work. Keep that allowance bounded.
        deadline = started + TIME_LIMIT_SECONDS + CONTAINER_OVERHEAD_SECONDS
        verdict: str | None = None
        while process.poll() is None:
            if time.monotonic() >= deadline:
                verdict = "TIME_LIMIT_EXCEEDED"
                _terminate_container(process, name)
                break
            for key, _ in selector.select(timeout=0.05):
                chunk = key.fileobj.read(4096)
                if chunk:
                    output.extend(chunk)
                    if len(output) > MAX_OUTPUT_BYTES:
                        verdict = "OUTPUT_LIMIT_EXCEEDED"
                        _terminate_container(process, name)
                        break
        remaining_budget = max(0, MAX_OUTPUT_BYTES - len(output))
        remaining = process.stdout.read(remaining_budget) if remaining_budget else b""
        remaining = remaining or b""
        output.extend(remaining)
        elapsed = int((time.monotonic() - started) * 1000)
        if verdict:
            return Execution(verdict, output[:MAX_OUTPUT_BYTES].decode(errors="replace"), elapsed)
        if process.returncode == 90:
            verdict = "COMPILATION_ERROR"
        elif process.returncode == 125:
            return Execution("SYSTEM_ERROR", "The judge runtime is unavailable.", elapsed)
        elif process.returncode == 137:
            verdict = "MEMORY_LIMIT_EXCEEDED"
        elif process.returncode != 0:
            verdict = "RUNTIME_ERROR"
        else:
            verdict = "COMPLETED"
        return Execution(verdict, output.decode(errors="replace"), elapsed)


def _prepare_source_directory(source_directory: Path) -> None:
    # Rootless Docker remaps container root and cannot traverse mkdtemp's 0700
    # directory or read its 0600 files. The read-only bind mount contains only
    # this submission's ephemeral source and evaluator inputs.
    source_directory.chmod(0o755)
    for item in source_directory.iterdir():
        if item.is_file():
            item.chmod(0o444)


def _terminate_container(process: subprocess.Popen, name: str) -> None:
    process.kill()
    process.wait(timeout=5)
    subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=5, check=False)


def outputs_match(actual: str, expected: str, tolerance: float | None = None) -> bool:
    if tolerance is not None:
        try:
            return abs(float(actual.strip()) - float(expected.strip())) <= tolerance
        except ValueError:
            return False
    return _normalize_console(actual) == _normalize_console(expected)


def _normalize_console(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return value[:-1] if value.endswith("\n") else value
