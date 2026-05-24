"""CLI commands for local IaC runner operations."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from terrapyne.core.runner_detection import resolve_runner

app = typer.Typer(help="Local IaC runner operations (terraform/opentofu).")


@app.command()
def info(
    directory: Annotated[
        Path, typer.Option("--directory", "-d", help="Workspace directory")
    ] = Path("."),
    force_runner: Annotated[
        Optional[str],
        typer.Option("--force-runner", help="Override heuristic detection"),
    ] = None,
) -> None:
    """Show detected IaC runner for the workspace."""
    resolved = resolve_runner(directory, force_runner=force_runner)
    typer.echo(f"Runner type: {resolved.runner_type}")
    typer.echo(f"Binary: {resolved.binary}")
    if resolved.version_constraint:
        typer.echo(f"Version constraint: {resolved.version_constraint}")
