"""Context resolution utilities for CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import typer

if TYPE_CHECKING:
    from terrapyne.api.client import TFCClient
from terrapyne.core.context import resolve_organization, resolve_workspace


def get_client(ctx: typer.Context | None, organization: str | None = None) -> "TFCClient":
    from terrapyne.api.client import TFCClient

    cache_ttl = 0
    if ctx and hasattr(ctx, "obj") and isinstance(ctx.obj, dict):
        cache_ttl = ctx.obj.get("cache_ttl", 0)
    return TFCClient(organization=organization, cache_ttl=cache_ttl)


def validate_context(
    organization: str | None = None,
    workspace: str | None = None,
    require_workspace: bool = False,
) -> tuple[str, str | None]:
    org = resolve_organization(organization)
    if not org:
        raise ValueError("No organization specified and could not detect from context.")
    ws = resolve_workspace(workspace)
    if require_workspace and not ws:
        raise ValueError("No workspace specified and could not detect from context.")
    return org, ws


def resolve_project_context(
    client: Any,
    organization: str | None = None,
    project_name: str | None = None,
) -> tuple[str, Any]:
    org, _ = validate_context(organization)
    if project_name:
        return org, client.projects.get_by_name(project_name, org)
    try:
        org, ws_name = validate_context(organization, require_workspace=True)
    except ValueError:
        raise ValueError(
            "No project specified and could not detect from workspace context."
        ) from None
    try:
        ws = client.workspaces.get(ws_name, org)
    except Exception as e:
        raise ValueError(f"Failed to fetch workspace '{ws_name}': {e}") from e
    if not ws.project_id:
        raise ValueError(f"Workspace '{ws_name}' is not assigned to a project.")
    return org, client.projects.get_by_id(ws.project_id)
