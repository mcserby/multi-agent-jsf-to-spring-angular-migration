"""Source-tree scanning utilities used by `init` to build context for the
Feature Mapper agent.

Deliberately shallow: we count files and list top-level directories. Deep
semantic understanding is left to the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


JSF_PAGE_GLOBS = ("**/*.xhtml", "**/*.jspx", "**/*.jsp")
JAVA_GLOB = "**/*.java"
TS_GLOB = "**/*.ts"


@dataclass
class SourceScan:
    root: Path
    files_by_pattern: dict[str, list[Path]] = field(default_factory=dict)

    @property
    def total_files(self) -> int:
        return sum(len(v) for v in self.files_by_pattern.values())

    def summary(self) -> str:
        if not self.root.exists():
            return f"{self.root}: (root does not exist)"
        lines = [f"{self.root}: {self.total_files} matching files"]
        for pat, files in self.files_by_pattern.items():
            lines.append(f"  {pat}: {len(files)}")
        return "\n".join(lines)


def _scan(root: Path, patterns: tuple[str, ...]) -> SourceScan:
    scan = SourceScan(root=root)
    if not root.exists():
        return scan
    for pat in patterns:
        scan.files_by_pattern[pat] = sorted(root.glob(pat))
    return scan


def scan_jsf(root: Path) -> SourceScan:
    return _scan(root, JSF_PAGE_GLOBS + (JAVA_GLOB,))


def scan_spring(root: Path) -> SourceScan:
    return _scan(root, (JAVA_GLOB,))


def scan_angular(root: Path) -> SourceScan:
    return _scan(root, (TS_GLOB, "**/*.html"))
