"""Debug CLI commands."""

import typer

from terrapyne.cli.utils import console

app = typer.Typer(help="Troubleshooting and debugging commands")


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("run")
def debug_run():
    """Diagnose run failures with log analysis."""
    console.print("[yellow]Coming soon: Run failure diagnostics (Priority 4)[/yellow]")


@app.command("workspace")
def debug_workspace():
    """Check workspace health and configuration."""
    console.print("[yellow]Coming soon: Workspace health checks (Priority 4)[/yellow]")
