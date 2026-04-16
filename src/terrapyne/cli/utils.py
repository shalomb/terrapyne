"""CLI utilities for shared error handling and context resolution."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import typer
from rich.console import Console

from terrapyne.utils.context import resolve_organization, resolve_workspace

F = TypeVar("F", bound=Callable[..., Any])

# Consolidated console instances for CLI output
# UI output goes to stdout (Typer default) to support test runners
console = Console()


def set_quiet_mode(quiet: bool) -> None:
    """Set quiet mode flag on the global console."""
    console.quiet = quiet


def handle_cli_errors(func: F) -> F:
    """Decorator to handle common CLI errors."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            raise
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1) from None
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(code=1) from None

    return wrapper  # type: ignore[return-value]


def validate_context(
    organization: str | None = None,
    workspace: str | None = None,
    require_workspace: bool = False,
) -> tuple[str, str | None]:
    """Validate and resolve organization and workspace context."""
    org = resolve_organization(organization)
    if not org:
        raise ValueError(
            "No organization specified and could not detect from context.\n"
            "Specify one of:\n"
            "  1. --organization ORGANIZATION flag\n"
            "  2. TFC_ORG environment variable (e.g., export TFC_ORG=my-org)\n"
            "  3. Run in a terraform directory with .terraform/terraform.tfstate or terraform.tf"
        )

    ws = resolve_workspace(workspace)
    if require_workspace and not ws:
        raise ValueError(
            "No workspace specified and could not detect from context.\n"
            "Either:\n"
            "  1. Run this command from a directory with terraform configuration (terraform.tf or .terraform/terraform.tfstate), or\n"
            "  2. Specify workspace name: --workspace WORKSPACE_NAME"
        )

    return org, ws


def emit_json(data):
    """Print data as JSON to stdout."""
    import json
    from datetime import datetime

    def _default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return str(obj)

    print(json.dumps(data, indent=2, default=_default))


def resolve_project_context(
    client: Any,
    organization: str | None = None,
    project_name: str | None = None,
) -> tuple[str, Any]:
    """Resolve organization and project from arguments or workspace context."""
    org, _ = validate_context(organization)

    if project_name:
        return org, client.projects.get_by_name(project_name, org)

    # Fallback: derive project from current workspace context
    try:
        org, ws_name = validate_context(organization, require_workspace=True)
    except ValueError:
        raise ValueError(
            "No project specified and could not detect from workspace context.\n"
            "Specify one of:\n"
            "  1. --project PROJECT_NAME flag\n"
            "  2. Run in a terraform directory with workspace configuration\n"
            "  3. Use a workspace that is assigned to a project"
        ) from None

    try:
        ws = client.workspaces.get(ws_name, org)  # type: ignore[arg-type]
    except Exception as e:
        raise ValueError(
            f"Failed to fetch workspace '{ws_name}' to resolve project context: {e}"
        ) from e

    if not ws.project_id:
        raise ValueError(
            f"Workspace '{ws_name}' is not assigned to a project.\n"
            f"To assign this workspace to a project:\n"
            f"  1. Visit: https://app.terraform.io/app/{org}/workspaces/{ws_name}/settings\n"
            f"  2. Select a project under 'Project'\n"
            f"  3. Click 'Save settings'"
        )

    return org, client.projects.get_by_id(ws.project_id)
