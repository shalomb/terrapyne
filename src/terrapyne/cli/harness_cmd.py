"""Harness commands for agent execution session management (ADR-007)."""

from __future__ import annotations

import os
import subprocess

import typer

from terrapyne.rendering.logging import error_console

harness_app = typer.Typer(
    name="harness",
    help="Agent harness and execution session management.",
)


@harness_app.command(
    "exec",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def harness_exec(
    ctx: typer.Context,
    allow_delete: str = typer.Option(
        ...,
        "--allow-delete",
        help="Comma-separated deletion classes to authorize (e.g. workspace, var, all)",
    ),
) -> None:
    """Execute a command within an authorized agent session grant.

    Examples:
        # Authorize workspace deletions for an agent session
        tfc harness exec --allow-delete=workspace -- claude

        # Authorize workspace deletions for a single command
        tfc harness exec --allow-delete=workspace -- tfc workspace delete dev-test --force
    """
    cmd = ctx.args
    if not cmd:
        error_console.print("[red]Error:[/red] No command specified to execute.")
        raise typer.Exit(code=1)

    env = dict(os.environ)
    existing = env.get("TERRAPYNE_ALLOW_DELETE", "")
    classes = [c.strip() for c in existing.split(",") if c.strip()]
    for c in allow_delete.split(","):
        cleaned = c.strip().lower()
        if cleaned and cleaned not in classes:
            classes.append(cleaned)
    env["TERRAPYNE_ALLOW_DELETE"] = ",".join(classes)

    result = subprocess.run(cmd, env=env)
    raise typer.Exit(code=result.returncode)
