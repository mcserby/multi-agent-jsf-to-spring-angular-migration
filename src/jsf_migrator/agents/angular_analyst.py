from __future__ import annotations

from pathlib import Path

from ..config import Feature
from .base import Agent, format_feature_files


class AngularAnalyst(Agent):
    name = "angular_analyst"
    prompt_template = "angular_analyst"

    def output_path(self, feature: Feature) -> Path:
        return self.project.paths.output / "specs" / "angular" / f"{feature.id}.json"

    def build_context(self, feature: Feature) -> dict[str, str]:
        src = self.project.source.angular
        return {
            "feature_id": feature.id,
            "feature_description": feature.description or "(none)",
            "angular_root": str(src.path),
            "angular_version": str(src.version),
            "component_style": src.component_style,
            "files_block": format_feature_files("angular", feature.angular),
        }
