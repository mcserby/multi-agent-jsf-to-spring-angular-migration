from pathlib import Path

import pytest
import yaml

from jsf_migrator.config import (
    ConfigError,
    Feature,
    ProjectConfig,
    dump_project_config,
    load_project_config,
)


def _minimal_raw(tmp_path: Path) -> dict:
    return {
        "source": {
            "jsf": {"path": str(tmp_path / "jsf")},
            "spring": {"path": str(tmp_path / "spring")},
            "angular": {"path": str(tmp_path / "angular")},
        }
    }


def test_load_minimal_config(tmp_path: Path):
    p = tmp_path / "project.yaml"
    p.write_text(yaml.safe_dump(_minimal_raw(tmp_path)), encoding="utf-8")
    cfg = load_project_config(p)
    assert cfg.version == 1
    assert cfg.source.jsf.bean_style == "CDI"
    assert cfg.gemini.yolo is True
    assert cfg.features == []


def test_load_missing_file(tmp_path: Path):
    with pytest.raises(ConfigError):
        load_project_config(tmp_path / "nope.yaml")


def test_load_rejects_unknown_keys(tmp_path: Path):
    raw = _minimal_raw(tmp_path)
    raw["mystery"] = "value"
    p = tmp_path / "project.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_project_config(p)


def test_roundtrip(tmp_path: Path):
    raw = _minimal_raw(tmp_path)
    raw["features"] = [{"id": "users", "description": "User CRUD", "approved": True}]
    p = tmp_path / "project.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")

    cfg = load_project_config(p)
    assert cfg.features[0].id == "users"

    out = tmp_path / "out.yaml"
    dump_project_config(cfg, out)
    reread = load_project_config(out)
    assert reread.features[0].id == "users"
    assert reread.features[0].approved is True


def test_feature_files_default_empty():
    f = Feature(id="x")
    assert f.jsf.pages == []
    assert f.spring.controllers == []


def test_quota_patterns_default():
    cfg = ProjectConfig(
        source={
            "jsf": {"path": "/tmp/j"},
            "spring": {"path": "/tmp/s"},
            "angular": {"path": "/tmp/a"},
        }
    )
    assert "RESOURCE_EXHAUSTED" in cfg.gemini.quota_patterns
