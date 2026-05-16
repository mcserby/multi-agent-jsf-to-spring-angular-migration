"""project.yaml schema and loader."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class JsfSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: Path
    framework_version: str = "JSF 2.x"
    bean_style: Literal["CDI", "ManagedBean", "Mixed"] = "CDI"


class SpringSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: Path
    java_version: int = 21
    package_root: str = ""


class AngularSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: Path
    version: int = 17
    component_style: Literal["standalone", "module"] = "standalone"


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jsf: JsfSource
    spring: SpringSource
    angular: AngularSource


class GeminiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = "gemini-2.5-pro"
    yolo: bool = True
    extra_args: list[str] = Field(default_factory=list)
    quota_patterns: list[str] = Field(
        default_factory=lambda: [
            "quota",
            "rate limit",
            "RESOURCE_EXHAUSTED",
            "429",
            "exceeded",
        ]
    )
    timeout_seconds: int = 900


class PathsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompts: Path = Path("./prompts")
    output: Path = Path("./migration-audit")


class FeatureFiles(BaseModel):
    """Glob patterns or paths (relative to the corresponding source root)."""
    model_config = ConfigDict(extra="forbid")
    pages: list[str] = Field(default_factory=list)
    beans: list[str] = Field(default_factory=list)
    controllers: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)


class Feature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    description: str = ""
    jsf: FeatureFiles = Field(default_factory=FeatureFiles)
    spring: FeatureFiles = Field(default_factory=FeatureFiles)
    angular: FeatureFiles = Field(default_factory=FeatureFiles)
    approved: bool = False


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 1
    source: SourceConfig
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    features: list[Feature] = Field(default_factory=list)


class ConfigError(Exception):
    pass


def load_project_config(path: Path) -> ProjectConfig:
    if not path.exists():
        raise ConfigError(f"project.yaml not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return ProjectConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"invalid project.yaml: {e}") from e


def dump_project_config(cfg: ProjectConfig, path: Path) -> None:
    raw = cfg.model_dump(mode="json", exclude_defaults=False)
    path.write_text(
        yaml.safe_dump(raw, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
