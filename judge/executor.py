import io
import os
import tarfile
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


def isolated_command(image: str, source_directory: Path, name: str, command: str, archive_size: int | None = None) -> list[str]:
    # Source files arrive over stdin. No host-path bind mount is required.
    if archive_size is not None:
        command = f"head -c {archive_size} | tar -xf - -C /source && {command}"
    return [
        "docker", "run", "--rm", "--interactive", "--name", name,
        "--pull", "never",
        "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--user", "65534:65534",
        "--security-opt", "no-new-privileges", "--pids-limit", "64",
        "--memory", "256m", "--memory-swap", "256m", "--cpus", "0.5",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m,mode=1777",
        "--tmpfs", "/work:rw,exec,nosuid,size=64m,mode=1777",
        "--tmpfs", "/source:rw,noexec,nosuid,size=64m,mode=1777",
        "--workdir", "/work",
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


def _source_archive(source_directory: Path) -> bytes:
    """Pack only regular submission files, using relative archive paths."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for item in sorted(source_directory.rglob("*")):
            if item.is_symlink():
                raise ValueError("Submission fixtures cannot contain symbolic links.")
            relative = item.relative_to(source_directory)
            if item.is_dir():
                continue
            if not item.is_file():
                raise ValueError("Unsupported submission fixture entry.")
            data = item.read_bytes()
            info = tarfile.TarInfo(relative.as_posix())
            info.size = len(data)
            info.mode = 0o444
            info.uid = info.gid = 65534
            archive.addfile(info, io.BytesIO(data))
    return stream.getvalue()


def run_container(image: str, source_directory: Path, command: str, input_data: str) -> Execution:
    """Stream source to an isolated container instead of bind-mounting judge /tmp."""
    name = f"eklavya-{uuid4().hex}"
    started = time.monotonic()
    try:
        archive = _source_archive(source_directory)
        payload = memoryview(archive + input_data.encode("utf-8"))
        process = subprocess.Popen(
            isolated_command(image, source_directory, name, command, len(archive)),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    except (OSError, ValueError) as error:
        return Execution("SYSTEM_ERROR", f"Judge runtime setup failed: {type(error).__name__}", 0)

    assert process.stdin is not None and process.stdout is not None
    selector = selectors.DefaultSelector()
    output = bytearray()
    verdict: str | None = None
    sent = 0
    try:
        os.set_blocking(process.stdin.fileno(), False)
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        if payload:
            selector.register(process.stdin, selectors.EVENT_WRITE)
        else:
            process.stdin.close()

        deadline = started + TIME_LIMIT_SECONDS + CONTAINER_OVERHEAD_SECONDS
        while selector.get_map():
            if time.monotonic() >= deadline:
                verdict = "TIME_LIMIT_EXCEEDED"
                _terminate_container(process, name)
                break
            for key, _ in selector.select(timeout=0.05):
                if key.fileobj is process.stdin:
                    try:
                        written = os.write(process.stdin.fileno(), payload[sent:sent + 65536])
                    except BrokenPipeError:
                        written = 0
                        sent = len(payload)
                    sent += written
                    if sent >= len(payload):
                        selector.unregister(process.stdin)
                        process.stdin.close()
                else:
                    try:
                        chunk = os.read(process.stdout.fileno(), 4096)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(process.stdout)
                    else:
                        output.extend(chunk)
                        if len(output) > MAX_OUTPUT_BYTES:
                            verdict = "OUTPUT_LIMIT_EXCEEDED"
                            _terminate_container(process, name)
                            break
            if verdict is not None:
                break
        if process.poll() is None:
            process.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        verdict = verdict or "SYSTEM_ERROR"
        _terminate_container(process, name)
    finally:
        selector.close()
        if not process.stdin.closed:
            process.stdin.close()
        process.stdout.close()

    elapsed = int((time.monotonic() - started) * 1000)
    if verdict:
        message = "Judge execution failed." if verdict == "SYSTEM_ERROR" else output[:MAX_OUTPUT_BYTES].decode(errors="replace")
        return Execution(verdict, message, elapsed)
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
