"""state.json — single source of truth for migration progress."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["pending", "in_progress", "completed", "failed", "interrupted"]
FeatureStatus = Literal["pending", "in_progress", "audited", "failed", "interrupted"]
Phase = Literal["init", "audit", "fix"]


class TaskState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: TaskStatus = "pending"
    output: str | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class FeatureState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: FeatureStatus = "pending"
    tasks: dict[str, TaskState] = Field(default_factory=dict)
    last_error: str | None = None


class State(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 1
    phase: Phase = "init"
    started_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())
    interrupted_reason: str | None = None
    features: dict[str, FeatureState] = Field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = _now()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state(path: Path) -> State:
    if not path.exists():
        return State()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return State.model_validate(raw)


def save_state(state: State, path: Path) -> None:
    state.touch()
    path.write_text(
        json.dumps(state.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
