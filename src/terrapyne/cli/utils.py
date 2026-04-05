"""CLI utilities for shared error handling and context resolution."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import typer
from rich.console import Console

from terrapyne.utils.context import resolve_organization, resolve_workspace

F = TypeVar("F", bound=Callable[..., Any])
console = Console()


def handle_cli_errors(func: F) -> F:
    """Decorator to handle common CLI errors.

    Handles:
    - ValueError: Missing context/arguments (converted to user-friendly message)
    - Exception: Generic errors

    Converts exceptions to console output and raises typer.Exit(1).
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            # Let typer.Exit propagate without modification (clean exit)
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
    """Validate and resolve organization and workspace context.

    This helper consolidates the common pattern of resolving organization
    and optionally workspace from CLI arguments or context detection.

    Args:
        organization: CLI argument for organization (optional).
            If None, attempts auto-detection from terraform.tf or tfstate.
        workspace: CLI argument for workspace (optional).
            If None, attempts auto-detection from tfstate.
        require_workspace: If True, raises ValueError if workspace cannot be resolved.

    Returns:
        Tuple of (organization, workspace).
        workspace will be None if not required and not resolved.
        If require_workspace=True, workspace is guaranteed to be a non-None string.

    Raises:
        ValueError: If organization cannot be resolved, or if workspace is required
            but cannot be resolved.

    Examples:
        # Just need organization
        org, _ = validate_context(organization)

        # Need both organization and workspace
        org, ws = validate_context(organization, workspace, require_workspace=True)
        # ws is guaranteed to be str, not str | None
    """
    org = resolve_organization(organization)
    if not org:
        raise ValueError(
            "No organization specified and could not detect from context. "
            "Specify: --organization ORGANIZATION or run in terraform directory."
        )

    if workspace or require_workspace:
        ws = resolve_workspace(workspace)
        if not ws and require_workspace:
            raise ValueError(
                "No workspace specified and could not detect from context. "
                "Specify: WORKSPACE or run in terraform directory."
            )
        return org, ws if ws else None  # type: ignore[return-value]

    return org, None


def emit_json(data):
    """Print data as JSON to stdout. Handles Pydantic models and datetimes."""
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
    """Resolve organization and project from arguments or workspace context.

    Args:
        client: Authenticated TFCClient instance
        organization: Optional organization name
        project_name: Optional project name. If None, falls back to workspace context.

    Returns:
        Tuple of (organization_name, Project model instance)

    Raises:
        ValueError: If project_name is None and workspace context cannot be resolved.
    """
    from terrapyne.api.projects import ProjectAPI
    from terrapyne.api.workspaces import WorkspaceAPI

    org, _ = validate_context(organization)
    project_api = ProjectAPI(client)

    if project_name:
        return org, project_api.get_by_name(project_name, org)

    # Fallback: derive project from current workspace context
    try:
        org, ws_name = validate_context(organization, require_workspace=True)
    except ValueError:
        raise ValueError(
            "No project specified and could not detect from workspace context. "
            "Specify a PROJECT_NAME or run in a terraform directory."
        ) from None

    workspace_api = WorkspaceAPI(client)
    try:
        ws = workspace_api.get(ws_name, org)  # type: ignore[arg-type]
    except Exception as e:
        raise ValueError(
            f"Failed to fetch workspace '{ws_name}' to resolve project context: {e}"
        ) from e

    if not ws.project_id:
        raise ValueError(f"Workspace '{ws_name}' is not assigned to a project.")

    return org, project_api.get_by_id(ws.project_id)
