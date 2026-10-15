"""Session-gated deletion safeguards for automated agents (ADR-007)."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import typer

from terrapyne.cli import agent_context
from terrapyne.rendering.logging import console, error_console

if TYPE_CHECKING:
    import typer


VALID_DELETE_CLASSES = frozenset({"workspace", "var", "varset", "team", "trigger", "api", "all"})


def is_deletion_granted(resource_class: str, env: dict[str, str] | None = None) -> bool:
    """Check if the given resource class is granted in the active deletion session.

    Args:
        resource_class: The class of resource being deleted (e.g. 'workspace', 'var').
        env: Environment mapping to inspect (defaults to os.environ).

    Returns:
        True if the session authorizes deleting the resource class, False otherwise.
    """
    if env is None:
        env = dict(os.environ)

    raw_grants = env.get("TERRAPYNE_ALLOW_DELETE", "")
    if not raw_grants:
        return False

    grants = {token.strip().lower() for token in raw_grants.split(",") if token.strip()}
    return "all" in grants or resource_class.strip().lower() in grants


def check_deletion_allowed(
    resource_class: str,
    ctx: typer.Context | None = None,
    output_format: str | None = None,
    env: dict[str, str] | None = None,
    stdout_isatty: bool | None = None,
) -> None:
    """Enforce session-gated deletion policy before performing destructive actions.

    If invoked in an automated/agent context and the resource class is not explicitly
    granted, immediately halts execution with an actionable refusal message.

    Args:
        resource_class: The class of resource being deleted (e.g. 'workspace', 'var').
        ctx: Optional Typer context.
        output_format: Requested output format if known.
        env: Environment mapping for testing/overrides.
        stdout_isatty: TTY detection override for testing.

    Raises:
        typer.Exit(1): If the deletion is not authorized in an agent context.
    """
    context: agent_context.AgentContext | None = None
    if ctx is not None and isinstance(ctx.obj, dict) and "agent_context" in ctx.obj:
        context = ctx.obj["agent_context"]

    if context is None:
        context = agent_context.detect(env=env, stdout_isatty=stdout_isatty)

    if not context.is_agent:
        # Human interactive terminal — allowed to proceed to prompt/force confirmation.
        return

    if is_deletion_granted(resource_class, env=env):
        # Human explicitly pre-authorized this resource class for this session.
        return

    # Determine if JSON format was requested
    is_json = False
    if output_format and output_format.lower() == "json":
        is_json = True
    elif ctx is not None:
        try:
            from terrapyne.cli.output_helpers import effective_format

            is_json = effective_format(ctx, "table") == "json"
        except Exception:
            pass

    refusal_msg = (
        f"[red]Refusal:[/red] Deletion of '{resource_class}' is gated in automated/agent sessions.\n"
        f"To authorize this deletion, run via:\n"
        f"  tfc harness exec --allow-delete={resource_class} -- <command>\n"
        f"or export:\n"
        f"  export TERRAPYNE_ALLOW_DELETE={resource_class}"
    )

    error_console.print(refusal_msg)

    if is_json:
        payload = {
            "error": "deletion_gated",
            "resource_class": resource_class,
            "message": f"Deletion of '{resource_class}' is gated in automated/agent sessions.",
            "hints": [
                f"Ask the human to authorize this session: tfc harness exec --allow-delete={resource_class} -- <command>",
                f"Or export TERRAPYNE_ALLOW_DELETE={resource_class} in the host environment",
            ],
        }
        console.print(json.dumps(payload, indent=2))

    raise typer.Exit(code=1)
