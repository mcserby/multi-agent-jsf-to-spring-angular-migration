from __future__ import annotations

from pathlib import Path

from ..config import Feature
from .base import Agent


class Comparator(Agent):
    name = "comparator"
    prompt_template = "comparator"

    def output_path(self, feature: Feature) -> Path:
        return self.project.paths.output / "gaps" / f"{feature.id}.md"

    def build_context(self, feature: Feature) -> dict[str, str]:
        base = self.project.paths.output
        return {
            "feature_id": feature.id,
            "feature_description": feature.description or "(none)",
            "jsf_spec_path": str(base / "specs" / "jsf" / f"{feature.id}.json"),
            "spring_spec_path": str(base / "specs" / "spring" / f"{feature.id}.json"),
            "angular_spec_path": str(base / "specs" / "angular" / f"{feature.id}.json"),
        }
