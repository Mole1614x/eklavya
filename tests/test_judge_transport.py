import io
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from judge.executor import _source_archive, isolated_command


def test_source_archive_preserves_nested_fixture_files():
    with TemporaryDirectory() as directory:
        source = Path(directory)
        (source / "fixture").mkdir()
        (source / "fixture" / "input.txt").write_text("hello", encoding="utf-8")
        (source / "main.py").write_text("print(1)", encoding="utf-8")
        payload = _source_archive(source)
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
            assert archive.extractfile("main.py").read() == b"print(1)"
            assert archive.extractfile("fixture/input.txt").read() == b"hello"


def test_runner_uses_stdin_transport_and_no_host_bind_mount():
    command = isolated_command(
        "python:3.12-alpine", Path("/tmp/unshared"), "test-judge",
        "exec python /source/main.py", archive_size=10240,
    )
    assert "--volume" not in command
    assert "/source:rw,noexec,nosuid,size=64m,mode=1777" in command
    assert "head -c 10240 | tar -xf - -C /source" in command[-1]
    assert "--network" in command and "none" in command


def test_archive_rejects_symlinks():
    with TemporaryDirectory() as directory:
        source = Path(directory)
        (source / "real.txt").write_text("content", encoding="utf-8")
        (source / "link.txt").symlink_to("real.txt")
        try:
            _source_archive(source)
        except ValueError:
            pass
        else:
            raise AssertionError("Symlink must not be accepted")
