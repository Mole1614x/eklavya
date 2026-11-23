import io
import tarfile
from pathlib import Path

from judge.executor import CONTAINER_OVERHEAD_SECONDS, TIME_LIMIT_SECONDS, _source_archive, container_command, outputs_match


def test_container_command_applies_isolation_controls(tmp_path):
    command = container_command("python", Path(tmp_path), "eklavya-test")
    joined = " ".join(command)
    for expected in ("--interactive", "--pull never", "--network none", "--read-only", "--cap-drop ALL",
                     "no-new-privileges", "--memory 256m", "--cpus 0.5", "mode=1777", "/source:rw,noexec"):
        assert expected in joined
    assert "python:3.12-alpine" in command
    assert "eklavya-code-runner:latest" in container_command("cpp", Path(tmp_path), "eklavya-cpp-test")


def test_console_comparison_preserves_whitespace_and_allows_final_newline():
    assert outputs_match("*\\n**\\n", "*\\n**")
    assert not outputs_match("* \\n**", "*\\n**")
    assert outputs_match("0.300001", "0.3", 0.00001)
    assert not outputs_match("0.31", "0.3", 0.00001)


def test_source_staging_is_container_readable_but_not_writable(tmp_path):
    source = tmp_path / "main.py"
    source.write_text("print('ready')", encoding="utf-8")
    archive = _source_archive(tmp_path)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        entry = bundle.getmember("main.py")
        assert entry.mode == 0o444
        assert bundle.extractfile(entry).read() == b"print('ready')"
    assert TIME_LIMIT_SECONDS == 5
    assert 0 < CONTAINER_OVERHEAD_SECONDS <= 2
