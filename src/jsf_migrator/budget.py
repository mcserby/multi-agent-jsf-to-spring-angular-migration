"""Graceful-stop logic: detect quota / rate-limit failures from gemini-cli output."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class QuotaCheck:
    is_quota_error: bool
    matched_pattern: str | None = None


def check_quota_error(
    stderr: str,
    stdout: str,
    exit_code: int,
    patterns: list[str],
) -> QuotaCheck:
    """Return whether the gemini-cli result looks like a quota/rate-limit failure.

    Non-zero exit alone isn't sufficient — gemini-cli can fail for many reasons.
    We require a non-zero exit AND a quota-shaped pattern in stderr or stdout.
    """
    if exit_code == 0:
        return QuotaCheck(False)
    haystack = f"{stderr}\n{stdout}"
    for pat in patterns:
        if re.search(pat, haystack, flags=re.IGNORECASE):
            return QuotaCheck(True, pat)
    return QuotaCheck(False)
