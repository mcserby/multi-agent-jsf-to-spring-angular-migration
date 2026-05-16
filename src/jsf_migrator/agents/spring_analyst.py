from __future__ import annotations

from pathlib import Path

from ..config import Feature
from .base import Agent, format_feature_files


class SpringAnalyst(Agent):
    name = "spring_analyst"
    prompt_template = "spring_analyst"

    def output_path(self, feature: Feature) -> Path:
        return self.project.paths.output / "specs" / "spring" / f"{feature.id}.json"

    def build_context(self, feature: Feature) -> dict[str, str]:
        src = self.project.source.spring
        return {
            "feature_id": feature.id,
            "feature_description": feature.description or "(none)",
            "spring_root": str(src.path),
            "java_version": str(src.java_version),
            "package_root": src.package_root or "(unspecified)",
            "files_block": format_feature_files("spring", feature.spring),
        }
