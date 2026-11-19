from pathlib import Path

from judge.executor import container_command, outputs_match


def test_container_command_applies_isolation_controls(tmp_path):
    command = container_command("python", Path(tmp_path), "eklavya-test")
    joined = " ".join(command)
    for expected in ("--network none", "--read-only", "--cap-drop ALL", "no-new-privileges", "--memory 256m", "--cpus 0.5", ":/source:ro"):
        assert expected in joined
    assert "python:3.12-alpine" in command


def test_console_comparison_preserves_whitespace_and_allows_final_newline():
    assert outputs_match("*\n**\n", "*\n**")
    assert not outputs_match("* \n**", "*\n**")
    assert outputs_match("0.300001", "0.3", 0.00001)
    assert not outputs_match("0.31", "0.3", 0.00001)
