"""Main CLI entry point for terrapyne."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from terrapyne.cli import (
    debug_cmd,
    project_cmd,
    run_cmd,
    state_cmd,
    team_cmd,
    vcs_cmd,
    workspace_cmd,
)
from terrapyne.cli.utils import console, set_quiet_mode

# Use the invocation name (e.g., "tfc" or "terrapyne") instead of hardcoded name
_prog = Path(sys.argv[0]).name
app = typer.Typer(
    name=_prog,
    help="Terraform Cloud CLI orchestrator for DevOps engineers",
)

# Add workspace commands
app.add_typer(workspace_cmd.app, name="workspace")

# Add run commands
app.add_typer(run_cmd.app, name="run")

# Add team commands
app.add_typer(team_cmd.app, name="team")

# Add VCS commands
app.add_typer(vcs_cmd.app, name="vcs")

# Add debug commands
app.add_typer(debug_cmd.app, name="debug")

# Add project commands
app.add_typer(project_cmd.app, name="project")

# Add state commands
app.add_typer(state_cmd.app, name="state")


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print("terrapyne version 0.1.0")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all UI output (data only)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable API call tracing and verbose logging",
    ),
) -> None:
    """Terraform Cloud CLI orchestrator for DevOps engineers."""
    from terrapyne.cli.utils import setup_logging

    set_quiet_mode(quiet)
    setup_logging(debug)
    if ctx.invoked_subcommand is None and not quiet:
        console.print(ctx.get_help())
