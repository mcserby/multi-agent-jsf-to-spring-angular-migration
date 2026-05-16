import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from jsf_migrator.config import GeminiConfig
from jsf_migrator.gemini_adapter import GeminiAdapter, GeminiUnavailable


def test_build_command_with_yolo_and_model():
    cfg = GeminiConfig(model="gemini-2.5-pro", yolo=True, extra_args=["--debug"])
    adapter = GeminiAdapter(cfg)
    cmd = adapter.build_command()
    assert cmd[0] == "gemini"
    assert "--yolo" in cmd
    assert "-m" in cmd and "gemini-2.5-pro" in cmd
    assert "--debug" in cmd


def test_dry_run_does_not_invoke_subprocess():
    cfg = GeminiConfig()
    adapter = GeminiAdapter(cfg, dry_run=True)
    with patch("subprocess.run") as run:
        result = adapter.run("hello world prompt", cwd=Path("."))
        run.assert_not_called()
    assert result.ok
    assert "DRY RUN" in result.stdout


def test_ensure_available_raises_when_missing():
    cfg = GeminiConfig()
    adapter = GeminiAdapter(cfg)
    with patch("jsf_migrator.gemini_adapter.shutil.which", return_value=None):
        with pytest.raises(GeminiUnavailable):
            adapter.ensure_available()


def test_run_pipes_prompt_via_stdin():
    cfg = GeminiConfig()
    adapter = GeminiAdapter(cfg)
    fake = subprocess.CompletedProcess(args=["gemini"], returncode=0, stdout="ok", stderr="")
    with patch("subprocess.run", return_value=fake) as run:
        adapter.run("PROMPT_BODY", cwd=Path("."))
    args, kwargs = run.call_args
    assert kwargs["input"] == "PROMPT_BODY"
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True


def test_run_detects_quota_error_from_stderr():
    cfg = GeminiConfig()
    adapter = GeminiAdapter(cfg)
    fake = subprocess.CompletedProcess(
        args=["gemini"], returncode=1, stdout="", stderr="HTTP 429 quota exceeded"
    )
    with patch("subprocess.run", return_value=fake):
        result = adapter.run("p", cwd=Path("."))
    assert result.quota.is_quota_error is True


def test_run_timeout_returns_124():
    cfg = GeminiConfig(timeout_seconds=1)
    adapter = GeminiAdapter(cfg)
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="gemini", timeout=1),
    ):
        result = adapter.run("p", cwd=Path("."))
    assert result.exit_code == 124
    assert "timed out" in result.stderr
