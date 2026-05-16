"""Spring fixer — phase 2, stubbed.

Reads an approved gap report for a feature and patches the Spring codebase to
close the gaps. Disabled in the current build; the orchestrator refuses to run
fix tasks until this is implemented.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Feature
from .base import Agent, AgentResult


class SpringFixer(Agent):
    name = "spring_fixer"
    prompt_template = "spring_fixer"
    implemented = False

    def output_path(self, feature: Feature) -> Path:
        return self.project.paths.output / "fixes" / "spring" / f"{feature.id}.md"

    def build_context(self, feature: Feature) -> dict[str, str]:
        return {
            "feature_id": feature.id,
            "gap_report": str(self.project.paths.output / "gaps" / f"{feature.id}.md"),
            "spring_root": str(self.project.source.spring.path),
        }

    def run(self, feature: Feature) -> AgentResult:
        raise NotImplementedError("SpringFixer is phase 2 and not yet implemented")
