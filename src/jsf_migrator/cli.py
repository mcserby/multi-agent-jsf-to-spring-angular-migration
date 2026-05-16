"""CLI entry point: `jsf-migrate <command>` run in the consuming project root."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .alignment import propose_features
from .config import (
    AngularSource,
    ConfigError,
    GeminiConfig,
    JsfSource,
    PathsConfig,
    ProjectConfig,
    SourceConfig,
    SpringSource,
    dump_project_config,
    load_project_config,
)
from .gemini_adapter import GeminiAdapter, GeminiUnavailable
from .orchestrator import AuditOrchestrator, QuotaExhausted
from .prompts import PromptLoader
from .state import State, load_state, save_state

DEFAULT_CONFIG_PATH = Path("project.yaml")
DEFAULT_STATE_PATH = Path("state.json")

console = Console()


# ---------------------------------------------------------------------------
# helpers

def _load_or_die(config_path: Path) -> ProjectConfig:
    try:
        return load_project_config(config_path)
    except ConfigError as e:
        console.print(f"[red]config error:[/red] {e}")
        sys.exit(2)


def _make_loader(project: ProjectConfig) -> PromptLoader:
    override = project.paths.prompts if project.paths.prompts.exists() else None
    return PromptLoader(project_prompt_dir=override)


def _make_gemini(project: ProjectConfig, dry_run: bool) -> GeminiAdapter:
    return GeminiAdapter(project.gemini, dry_run=dry_run)


# ---------------------------------------------------------------------------
# commands

@click.group()
@click.version_option(package_name="jsf-migrator")
def main() -> None:
    """jsf-migrator — audit (and later fix) a JSF -> Spring Boot + Angular rewrite."""


@main.command()
@click.option("--jsf", "jsf_path", type=click.Path(path_type=Path), help="Path to legacy JSF root")
@click.option("--spring", "spring_path", type=click.Path(path_type=Path), help="Path to Spring Boot root")
@click.option("--angular", "angular_path", type=click.Path(path_type=Path), help="Path to Angular root")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=DEFAULT_CONFIG_PATH, show_default=True)
@click.option("--state", "state_path", type=click.Path(path_type=Path), default=DEFAULT_STATE_PATH, show_default=True)
@click.option("--skip-mapper", is_flag=True, help="Write a blank project.yaml; don't call gemini to propose features")
@click.option("--dry-run", is_flag=True, help="Show the gemini command instead of running it")
def init(
    jsf_path: Path | None,
    spring_path: Path | None,
    angular_path: Path | None,
    config_path: Path,
    state_path: Path,
    skip_mapper: bool,
    dry_run: bool,
) -> None:
    """Bootstrap project.yaml + state.json, then auto-propose feature mappings."""
    if config_path.exists():
        console.print(f"[yellow]{config_path} already exists.[/yellow] Edit it manually or delete it before re-running init.")
        sys.exit(1)

    if not (jsf_path and spring_path and angular_path):
        console.print("[red]--jsf, --spring and --angular paths are required on first init.[/red]")
        sys.exit(2)

    project = ProjectConfig(
        source=SourceConfig(
            jsf=JsfSource(path=jsf_path),
            spring=SpringSource(path=spring_path),
            angular=AngularSource(path=angular_path),
        ),
        gemini=GeminiConfig(),
        paths=PathsConfig(),
    )
    dump_project_config(project, config_path)
    save_state(State(phase="init"), state_path)
    console.print(f"[green]wrote {config_path} and {state_path}[/green]")

    if skip_mapper:
        console.print("[dim]--skip-mapper set; you can add features: entries manually.[/dim]")
        return

    prompts = _make_loader(project)
    gemini = _make_gemini(project, dry_run=dry_run)
    try:
        gemini.ensure_available()
    except GeminiUnavailable as e:
        console.print(f"[yellow]skipping mapper: {e}[/yellow]")
        return

    console.print("[cyan]running feature mapper...[/cyan]")
    result, proposed = propose_features(project, gemini, prompts, config_path)
    if not result.ok:
        console.print(f"[red]mapper failed (exit {result.exit_code}):[/red]\n{result.stderr[-1000:]}")
        sys.exit(1)
    console.print(f"[green]mapper proposed {len(proposed)} features.[/green] Review {config_path} and set `approved: true` on the ones you want audited.")


@main.command()
@click.option("--feature", "only", help="Audit only this feature id (ignores approved flag)")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=DEFAULT_CONFIG_PATH, show_default=True)
@click.option("--state", "state_path", type=click.Path(path_type=Path), default=DEFAULT_STATE_PATH, show_default=True)
@click.option("--dry-run", is_flag=True, help="Show the gemini command instead of running it")
def audit(only: str | None, config_path: Path, state_path: Path, dry_run: bool) -> None:
    """Run the analyst + comparator pipeline over approved features."""
    project = _load_or_die(config_path)
    state = load_state(state_path)
    prompts = _make_loader(project)
    gemini = _make_gemini(project, dry_run=dry_run)

    orchestrator = AuditOrchestrator(project, state, gemini, prompts)
    exit_code = 0
    try:
        for report in orchestrator.run(only=only):
            marker = "[green]ok[/green]" if report.ok else "[red]fail[/red]"
            console.print(f"  {marker} {report.feature_id} :: {report.step}")
            if not report.ok and report.error:
                console.print(f"    [dim]{report.error[:300]}[/dim]")
            save_state(state, state_path)
    except QuotaExhausted as e:
        console.print(f"\n[yellow]quota exhausted — stopping gracefully.[/yellow] {e}")
        console.print("[dim]run `jsf-migrate resume` after quota refreshes.[/dim]")
        exit_code = 3
    finally:
        save_state(state, state_path)

    sys.exit(exit_code)


@main.command()
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=DEFAULT_CONFIG_PATH, show_default=True)
@click.option("--state", "state_path", type=click.Path(path_type=Path), default=DEFAULT_STATE_PATH, show_default=True)
@click.option("--dry-run", is_flag=True)
def resume(config_path: Path, state_path: Path, dry_run: bool) -> None:
    """Continue an audit run that stopped (quota or otherwise)."""
    ctx = click.get_current_context()
    ctx.invoke(audit, only=None, config_path=config_path, state_path=state_path, dry_run=dry_run)


@main.command()
@click.option("--state", "state_path", type=click.Path(path_type=Path), default=DEFAULT_STATE_PATH, show_default=True)
def status(state_path: Path) -> None:
    """Print a summary of state.json."""
    if not state_path.exists():
        console.print(f"[yellow]{state_path} not found — run `jsf-migrate init` first.[/yellow]")
        sys.exit(1)
    state = load_state(state_path)

    console.print(f"phase: [cyan]{state.phase}[/cyan]   updated: {state.updated_at}")
    if state.interrupted_reason:
        console.print(f"[yellow]interrupted:[/yellow] {state.interrupted_reason}")

    table = Table(title="features")
    table.add_column("id")
    table.add_column("status")
    for step, _ in [("jsf_analysis", None), ("spring_analysis", None), ("angular_analysis", None), ("comparison", None)]:
        table.add_column(step)
    for fid, fstate in state.features.items():
        row = [fid, fstate.status]
        for step in ("jsf_analysis", "spring_analysis", "angular_analysis", "comparison"):
            t = fstate.tasks.get(step)
            row.append(t.status if t else "-")
        table.add_row(*row)
    console.print(table)


@main.command()
@click.option("--feature", "only", required=True, help="Feature id to fix")
def fix(only: str) -> None:
    """Phase 2 — apply fixer agents. Currently stubbed."""
    console.print(
        "[yellow]phase 2 (fixers) is not implemented yet.[/yellow] "
        "Audit reports under `migration-audit/gaps/` are review-ready; apply fixes manually for now."
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
