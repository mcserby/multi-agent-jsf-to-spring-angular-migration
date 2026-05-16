from __future__ import annotations

from pathlib import Path

from ..config import Feature
from .base import Agent, format_feature_files


class JsfAnalyst(Agent):
    name = "jsf_analyst"
    prompt_template = "jsf_analyst"

    def output_path(self, feature: Feature) -> Path:
        return self.project.paths.output / "specs" / "jsf" / f"{feature.id}.json"

    def build_context(self, feature: Feature) -> dict[str, str]:
        src = self.project.source.jsf
        return {
            "feature_id": feature.id,
            "feature_description": feature.description or "(none)",
            "jsf_root": str(src.path),
            "framework_version": src.framework_version,
            "bean_style": src.bean_style,
            "files_block": format_feature_files("jsf", feature.jsf),
        }
