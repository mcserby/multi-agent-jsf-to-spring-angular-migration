"""Auto-propose feature mappings by delegating to the Feature Mapper agent.

This module is intentionally thin: it builds a prompt context, calls gemini-cli,
and merges the proposed YAML fragment into project.yaml. The actual reasoning
lives in the LLM with the bundled `feature_mapper.md` prompt.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import Feature, ProjectConfig, dump_project_config
from .gemini_adapter import GeminiAdapter, GeminiResult
from .planner import scan_angular, scan_jsf, scan_spring
from .prompts import PromptLoader


class AlignmentError(Exception):
    pass


def propose_features(
    project: ProjectConfig,
    gemini: GeminiAdapter,
    prompts: PromptLoader,
    project_yaml_path: Path,
) -> tuple[GeminiResult, list[Feature]]:
    """Run the Feature Mapper and merge its output into the project config.

    Returns the raw gemini result plus the parsed proposed features. If the
    config already has features (e.g. on re-run), they are preserved and the
    new proposals are appended with a `_proposed` suffix so the human can
    diff before keeping them.
    """
    scans = {
        "jsf": scan_jsf(project.source.jsf.path),
        "spring": scan_spring(project.source.spring.path),
        "angular": scan_angular(project.source.angular.path),
    }

    output_path = project.paths.output / "proposed-features.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    context = {
        "jsf_root": str(project.source.jsf.path),
        "spring_root": str(project.source.spring.path),
        "angular_root": str(project.source.angular.path),
        "output_path": str(output_path),
        "scan_jsf": scans["jsf"].summary(),
        "scan_spring": scans["spring"].summary(),
        "scan_angular": scans["angular"].summary(),
    }
    prompt = prompts.render("feature_mapper", context)
    result = gemini.run(prompt, cwd=Path.cwd())

    proposed: list[Feature] = []
    if result.ok and output_path.exists():
        proposed = _parse_proposed_features(output_path)
        if proposed:
            _merge_into_project(project, proposed, project_yaml_path)
    return result, proposed


def _parse_proposed_features(yaml_path: Path) -> list[Feature]:
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise AlignmentError(
            f"{yaml_path} must contain a YAML list of feature entries, got {type(raw).__name__}"
        )
    return [Feature.model_validate(entry) for entry in raw]


def _merge_into_project(
    project: ProjectConfig,
    proposed: list[Feature],
    project_yaml_path: Path,
) -> None:
    existing_ids = {f.id for f in project.features}
    for feat in proposed:
        if feat.id in existing_ids:
            feat.id = f"{feat.id}_proposed"
        project.features.append(feat)
    dump_project_config(project, project_yaml_path)
