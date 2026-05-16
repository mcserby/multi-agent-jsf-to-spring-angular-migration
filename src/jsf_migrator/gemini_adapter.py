"""Subprocess wrapper around official `gemini` CLI (Google, ~v0.42).

All knowledge of gemini-cli flags lives here so that v0.42 specifics can be
adjusted in one place if/when the actual CLI differs.

Invocation model: one call = one agent step.
The prompt is passed via stdin (safer than -p for long prompts that may include
source code). gemini-cli's `--yolo` flag auto-approves tool use so the agent can
read/write files inside its own loop without prompting.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .budget import QuotaCheck, check_quota_error
from .config import GeminiConfig


@dataclass
class GeminiResult:
    exit_code: int
    stdout: str
    stderr: str
    quota: QuotaCheck

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class GeminiUnavailable(Exception):
    pass


class GeminiAdapter:
    def __init__(self, config: GeminiConfig, *, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run

    def ensure_available(self) -> None:
        if self.dry_run:
            return
        if shutil.which("gemini") is None:
            raise GeminiUnavailable(
                "gemini-cli not found on PATH. Install Google's official @google/gemini-cli "
                "and authenticate (`gemini auth login` or GEMINI_API_KEY env var) before running."
            )

    def build_command(self) -> list[str]:
        cmd: list[str] = ["gemini"]
        if self.config.yolo:
            cmd.append("--yolo")
        if self.config.model:
            cmd += ["-m", self.config.model]
        cmd += list(self.config.extra_args)
        return cmd

    def run(self, prompt: str, *, cwd: Path | None = None) -> GeminiResult:
        cmd = self.build_command()

        if self.dry_run:
            preview = prompt if len(prompt) <= 400 else prompt[:400] + f"... [+{len(prompt)-400} chars]"
            stdout = (
                f"[DRY RUN] would invoke: {' '.join(cmd)}\n"
                f"[DRY RUN] cwd: {cwd or Path.cwd()}\n"
                f"[DRY RUN] prompt preview:\n{preview}\n"
            )
            return GeminiResult(0, stdout, "", QuotaCheck(False))

        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                cwd=str(cwd) if cwd else None,
                timeout=self.config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            return GeminiResult(
                exit_code=124,
                stdout=e.stdout or "",
                stderr=f"timed out after {self.config.timeout_seconds}s",
                quota=QuotaCheck(False),
            )

        quota = check_quota_error(
            stderr=proc.stderr,
            stdout=proc.stdout,
            exit_code=proc.returncode,
            patterns=self.config.quota_patterns,
        )
        return GeminiResult(proc.returncode, proc.stdout, proc.stderr, quota)
