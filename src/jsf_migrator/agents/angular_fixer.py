"""Angular fixer — phase 2, stubbed. Mirror of SpringFixer."""

from __future__ import annotations

from pathlib import Path

from ..config import Feature
from .base import Agent, AgentResult


class AngularFixer(Agent):
    name = "angular_fixer"
    prompt_template = "angular_fixer"
    implemented = False

    def output_path(self, feature: Feature) -> Path:
        return self.project.paths.output / "fixes" / "angular" / f"{feature.id}.md"

    def build_context(self, feature: Feature) -> dict[str, str]:
        return {
            "feature_id": feature.id,
            "gap_report": str(self.project.paths.output / "gaps" / f"{feature.id}.md"),
            "angular_root": str(self.project.source.angular.path),
        }

    def run(self, feature: Feature) -> AgentResult:
        raise NotImplementedError("AngularFixer is phase 2 and not yet implemented")
