"""Audit-phase state machine.

Walks the feature list, runs each agent in sequence (JSF -> Spring -> Angular ->
Comparator), records progress to state.json after every step, and exits cleanly
when gemini-cli reports quota exhaustion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .agents import AngularAnalyst, Comparator, JsfAnalyst, SpringAnalyst
from .agents.base import Agent
from .config import Feature, ProjectConfig
from .gemini_adapter import GeminiAdapter
from .prompts import PromptLoader
from .state import State, TaskState

AUDIT_STEPS: tuple[tuple[str, type[Agent]], ...] = (
    ("jsf_analysis", JsfAnalyst),
    ("spring_analysis", SpringAnalyst),
    ("angular_analysis", AngularAnalyst),
    ("comparison", Comparator),
)


class QuotaExhausted(Exception):
    """Raised to unwind cleanly when gemini-cli reports quota exhaustion."""

    def __init__(self, message: str, pattern: str | None):
        super().__init__(message)
        self.pattern = pattern


@dataclass
class StepReport:
    feature_id: str
    step: str
    ok: bool
    exit_code: int
    output_path: str | None
    error: str | None


class AuditOrchestrator:
    def __init__(
        self,
        project: ProjectConfig,
        state: State,
        gemini: GeminiAdapter,
        prompts: PromptLoader,
    ):
        self.project = project
        self.state = state
        self.gemini = gemini
        self.prompts = prompts

    def features_to_run(self, only: str | None = None) -> list[Feature]:
        feats = self.project.features
        if only:
            feats = [f for f in feats if f.id == only]
            if not feats:
                raise ValueError(f"no feature with id '{only}' in project.yaml")
        return [f for f in feats if f.approved or only is not None]

    def run(self, *, only: str | None = None) -> Iterable[StepReport]:
        self.gemini.ensure_available()
        self.state.phase = "audit"
        self.state.interrupted_reason = None

        for feature in self.features_to_run(only=only):
            fstate = self.state.features.setdefault(feature.id, _new_feature_state())
            if fstate.status == "audited" and not only:
                continue
            fstate.status = "in_progress"

            for step_name, agent_cls in AUDIT_STEPS:
                tstate = fstate.tasks.setdefault(step_name, TaskState())
                if tstate.status == "completed" and not only:
                    continue

                tstate.status = "in_progress"
                tstate.started_at = _now()

                agent = agent_cls(self.gemini, self.prompts, self.project)
                try:
                    result = agent.run(feature)
                except NotImplementedError as e:
                    tstate.status = "failed"
                    tstate.error = str(e)
                    fstate.status = "failed"
                    fstate.last_error = str(e)
                    yield StepReport(feature.id, step_name, False, -1, None, str(e))
                    return

                if result.gemini.quota.is_quota_error:
                    tstate.status = "interrupted"
                    tstate.error = f"quota: {result.gemini.quota.matched_pattern}"
                    fstate.status = "interrupted"
                    self.state.interrupted_reason = (
                        f"gemini-cli quota exhausted while running {step_name} "
                        f"for feature {feature.id} (pattern: {result.gemini.quota.matched_pattern})"
                    )
                    yield StepReport(
                        feature.id, step_name, False,
                        result.gemini.exit_code,
                        str(result.output_path) if result.output_path else None,
                        tstate.error,
                    )
                    raise QuotaExhausted(self.state.interrupted_reason, result.gemini.quota.matched_pattern)

                if not result.ok:
                    tstate.status = "failed"
                    tstate.error = (result.gemini.stderr or "")[-2000:]
                    fstate.status = "failed"
                    fstate.last_error = tstate.error
                    yield StepReport(
                        feature.id, step_name, False,
                        result.gemini.exit_code,
                        str(result.output_path) if result.output_path else None,
                        tstate.error,
                    )
                    return

                tstate.status = "completed"
                tstate.completed_at = _now()
                tstate.output = str(result.output_path) if result.output_path else None
                tstate.error = None

                yield StepReport(
                    feature.id, step_name, True,
                    result.gemini.exit_code,
                    tstate.output,
                    None,
                )

            if all(t.status == "completed" for t in fstate.tasks.values()):
                fstate.status = "audited"


def _new_feature_state():
    from .state import FeatureState  # local import to avoid cycle on type checkers
    return FeatureState(status="pending", tasks={})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
