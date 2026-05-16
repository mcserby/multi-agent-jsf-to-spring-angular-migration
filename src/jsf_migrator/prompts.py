"""Prompt template loader with project-override search path.

Templates are markdown files using $name / ${name} placeholders (string.Template
syntax — chosen over jinja2 so curly-brace code snippets in prompts are safe).
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from string import Template


class PromptNotFound(Exception):
    pass


class PromptLoader:
    """Resolves a prompt name to a markdown template.

    Search order:
        1. <project_prompt_dir>/<name>.md   (consuming project's override)
        2. bundled defaults inside the jsf_migrator package
    """

    def __init__(self, project_prompt_dir: Path | None = None):
        self.project_prompt_dir = project_prompt_dir

    def load(self, name: str) -> str:
        if self.project_prompt_dir:
            override = self.project_prompt_dir / f"{name}.md"
            if override.exists():
                return override.read_text(encoding="utf-8")
        try:
            return (
                resources.files("jsf_migrator._bundled_prompts")
                .joinpath(f"{name}.md")
                .read_text(encoding="utf-8")
            )
        except (FileNotFoundError, ModuleNotFoundError) as e:
            raise PromptNotFound(f"no bundled or override prompt for '{name}'") from e

    def render(self, name: str, context: dict[str, str]) -> str:
        return Template(self.load(name)).safe_substitute(context)
