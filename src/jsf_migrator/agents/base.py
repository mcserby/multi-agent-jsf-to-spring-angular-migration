"""Agent base class.

Each agent role:
  - declares its name and prompt template name
  - builds the per-task context dict that hydrates the prompt
  - delegates the actual LLM call to GeminiAdapter
  - declares its output artifact path so the orchestrator can record it
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ..config import Feature, ProjectConfig
from ..gemini_adapter import GeminiAdapter, GeminiResult
from ..prompts import PromptLoader


@dataclass
class AgentResult:
    ok: bool
    output_path: Path | None
    gemini: GeminiResult


class Agent:
    name: ClassVar[str] = "agent"
    prompt_template: ClassVar[str] = ""

    def __init__(self, gemini: GeminiAdapter, prompts: PromptLoader, project: ProjectConfig):
        self.gemini = gemini
        self.prompts = prompts
        self.project = project

    def output_path(self, feature: Feature) -> Path:
        raise NotImplementedError

    def build_context(self, feature: Feature) -> dict[str, str]:
        raise NotImplementedError

    def working_dir(self, feature: Feature) -> Path:
        return Path.cwd()

    def run(self, feature: Feature) -> AgentResult:
        out = self.output_path(feature)
        out.parent.mkdir(parents=True, exist_ok=True)
        context = self.build_context(feature)
        context.setdefault("output_path", str(out))
        prompt = self.prompts.render(self.prompt_template, context)
        result = self.gemini.run(prompt, cwd=self.working_dir(feature))
        return AgentResult(
            ok=result.ok and (self.gemini.dry_run or out.exists()),
            output_path=out,
            gemini=result,
        )


def _join(items: list[str]) -> str:
    if not items:
        return "(none)"
    return "\n".join(f"  - {x}" for x in items)


def format_feature_files(label: str, files) -> str:
    """Render a FeatureFiles object as a markdown block for a prompt."""
    return (
        f"{label}:\n"
        f"  pages:\n{_join(files.pages)}\n"
        f"  beans:\n{_join(files.beans)}\n"
        f"  controllers:\n{_join(files.controllers)}\n"
        f"  services:\n{_join(files.services)}\n"
        f"  components:\n{_join(files.components)}\n"
        f"  other:\n{_join(files.other)}\n"
    )
