"""Main CLI application."""

import typer
from rich.console import Console

from terrapyne.cli import debug_cmd, project_cmd, run_cmd, team_cmd, vcs_cmd, workspace_cmd

app = typer.Typer(
    name="terrapyne",
    help="Terraform Cloud CLI orchestrator for DevOps engineers",
    no_args_is_help=True,
)
console = Console()

# Add workspace commands
app.add_typer(workspace_cmd.app, name="workspace")

# Add run commands
app.add_typer(run_cmd.app, name="run")

# Add team commands
app.add_typer(team_cmd.app, name="team")

# Add VCS commands (placeholder)
app.add_typer(vcs_cmd.app, name="vcs")

# Add debug commands (placeholder)
app.add_typer(debug_cmd.app, name="debug")

# Add project commands (placeholder)
app.add_typer(project_cmd.app, name="project")


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print("terrapyne version 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Terraform Cloud CLI orchestrator for DevOps engineers.

    Context-aware commands that auto-detect workspace and organization from terraform.tf.
    """
    pass
