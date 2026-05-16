from pathlib import Path
from unittest.mock import patch

import pytest

from jsf_migrator.agents.base import AgentResult
from jsf_migrator.budget import QuotaCheck
from jsf_migrator.config import (
    AngularSource,
    Feature,
    GeminiConfig,
    JsfSource,
    PathsConfig,
    ProjectConfig,
    SourceConfig,
    SpringSource,
)
from jsf_migrator.gemini_adapter import GeminiAdapter, GeminiResult
from jsf_migrator.orchestrator import AuditOrchestrator, QuotaExhausted
from jsf_migrator.prompts import PromptLoader
from jsf_migrator.state import State


def _project(tmp_path: Path, approved: bool = True) -> ProjectConfig:
    return ProjectConfig(
        source=SourceConfig(
            jsf=JsfSource(path=tmp_path / "jsf"),
            spring=SpringSource(path=tmp_path / "spring"),
            angular=AngularSource(path=tmp_path / "angular"),
        ),
        gemini=GeminiConfig(),
        paths=PathsConfig(output=tmp_path / "audit"),
        features=[Feature(id="users", description="user crud", approved=approved)],
    )


def _ok_result() -> AgentResult:
    return AgentResult(
        ok=True,
        output_path=Path("out.json"),
        gemini=GeminiResult(0, "ok", "", QuotaCheck(False)),
    )


def _quota_result() -> AgentResult:
    return AgentResult(
        ok=False,
        output_path=Path("out.json"),
        gemini=GeminiResult(1, "", "429", QuotaCheck(True, "429")),
    )


def test_audit_runs_all_steps_for_approved_feature(tmp_path: Path):
    project = _project(tmp_path)
    state = State()
    gemini = GeminiAdapter(project.gemini, dry_run=True)
    prompts = PromptLoader()

    orch = AuditOrchestrator(project, state, gemini, prompts)
    with patch("jsf_migrator.orchestrator.JsfAnalyst.run", return_value=_ok_result()), \
         patch("jsf_migrator.orchestrator.SpringAnalyst.run", return_value=_ok_result()), \
         patch("jsf_migrator.orchestrator.AngularAnalyst.run", return_value=_ok_result()), \
         patch("jsf_migrator.orchestrator.Comparator.run", return_value=_ok_result()):
        reports = list(orch.run())

    assert [r.step for r in reports] == ["jsf_analysis", "spring_analysis", "angular_analysis", "comparison"]
    assert all(r.ok for r in reports)
    assert state.features["users"].status == "audited"


def test_audit_skips_unapproved_features(tmp_path: Path):
    project = _project(tmp_path, approved=False)
    state = State()
    gemini = GeminiAdapter(project.gemini, dry_run=True)
    orch = AuditOrchestrator(project, state, gemini, PromptLoader())
    reports = list(orch.run())
    assert reports == []


def test_audit_runs_unapproved_when_explicitly_targeted(tmp_path: Path):
    project = _project(tmp_path, approved=False)
    state = State()
    gemini = GeminiAdapter(project.gemini, dry_run=True)
    orch = AuditOrchestrator(project, state, gemini, PromptLoader())
    with patch("jsf_migrator.orchestrator.JsfAnalyst.run", return_value=_ok_result()), \
         patch("jsf_migrator.orchestrator.SpringAnalyst.run", return_value=_ok_result()), \
         patch("jsf_migrator.orchestrator.AngularAnalyst.run", return_value=_ok_result()), \
         patch("jsf_migrator.orchestrator.Comparator.run", return_value=_ok_result()):
        reports = list(orch.run(only="users"))
    assert len(reports) == 4


def test_quota_error_raises_and_marks_interrupted(tmp_path: Path):
    project = _project(tmp_path)
    state = State()
    gemini = GeminiAdapter(project.gemini, dry_run=True)
    orch = AuditOrchestrator(project, state, gemini, PromptLoader())
    with patch("jsf_migrator.orchestrator.JsfAnalyst.run", return_value=_quota_result()):
        with pytest.raises(QuotaExhausted):
            list(orch.run())
    assert state.features["users"].status == "interrupted"
    assert state.interrupted_reason is not None
    assert "429" in state.interrupted_reason


def test_unknown_feature_id_raises(tmp_path: Path):
    project = _project(tmp_path)
    state = State()
    gemini = GeminiAdapter(project.gemini, dry_run=True)
    orch = AuditOrchestrator(project, state, gemini, PromptLoader())
    with pytest.raises(ValueError):
        list(orch.run(only="nope"))
