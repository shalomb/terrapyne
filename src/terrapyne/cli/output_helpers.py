"""Output formatting and logging setup for CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terrapyne.rendering.logging import console, error_console

if TYPE_CHECKING:
    import typer
    from rich.console import Console

    from terrapyne.cli.agent_context import AgentContext


def set_console(new_console: Console) -> None:
    console._width = new_console.width
    console.legacy_windows = False
    error_console._width = new_console.width
    error_console.legacy_windows = False
    if hasattr(new_console, "force_terminal"):
        console._force_terminal = new_console.force_terminal
        error_console._force_terminal = new_console.force_terminal
    elif hasattr(new_console, "_force_terminal"):
        console._force_terminal = new_console._force_terminal
        error_console._force_terminal = new_console._force_terminal


def set_quiet_mode(quiet: bool) -> None:
    console.quiet = quiet
    error_console.quiet = quiet


def configure_for_agent_context() -> "AgentContext":
    """Detect agent context and reconfigure the shared console accordingly.

    When running under an agent harness or automation pipeline:
    - Rich markup and colour are suppressed (no ANSI in piped output)
    - Progress/spinner output is quieted
    - The detected context is returned so the CLI callback can store it

    Returns the AgentContext so the caller can log the reason and store it
    in ctx.obj for commands to read.
    """
    from terrapyne.cli.agent_context import detect

    ctx = detect()

    if ctx.is_agent:
        # Suppress colour and terminal markup — agents consume plain text or JSON
        console._force_terminal = False
        console.no_color = True
        error_console._force_terminal = False
        error_console.no_color = True

    return ctx


def setup_logging(debug: bool = False) -> None:
    if debug:
        import logging
        import os

        from terrapyne.rendering.logging import MultiFormatter

        os.environ["TERRAPYNE_DEBUG"] = "1"
        logger = logging.getLogger("terrapyne")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(MultiFormatter())
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)


def effective_format(ctx: "typer.Context", requested: str) -> str:
    """Resolve the effective output format for a command.

    If the user explicitly passed --format, that wins.  Otherwise, when running
    under an agent/automation context the default is "json" so agents get
    machine-readable output without having to pass --format json every time.
    """
    import click

    # If the user supplied --format explicitly, honour it unconditionally.
    if ctx.get_parameter_source("output_format") == click.core.ParameterSource.COMMANDLINE:
        return requested

    agent_ctx = (ctx.obj or {}).get("agent_context")
    if agent_ctx and agent_ctx.is_agent and requested == "table":
        return "json"

    return requested


def emit_json(data):
    import json
    from datetime import datetime

    def _default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return str(obj)

    print(json.dumps(data, indent=2, default=_default))
