"""Org-wide errored workspace discovery.

Uses a single paginated workspace list call with filter[current-run][status]=errored
rather than iterating every project and workspace individually.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terrapyne.api.client import TFCClient
    from terrapyne.models.workspace import Workspace


def get_errored_workspaces(
    client: "TFCClient",
    days: int = 7,
    project_id: str | None = None,
    organization: str | None = None,
) -> list["Workspace"]:
    """Return workspaces whose latest run is errored, within the lookback window.

    Makes a single paginated API call using filter[current-run][status]=errored,
    which is far more efficient than iterating projects and fetching runs per workspace.

    Args:
        client: Authenticated TFC API client.
        days: Only include workspaces whose latest run errored within this many days.
        project_id: If given, scope the scan to a single project.
        organization: Override the client's default organisation.

    Returns:
        List of Workspace instances with latest_run populated.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    workspaces_iter, _ = client.workspaces.list(
        organization=organization,
        current_run_status="errored",
        project_id=project_id,
    )

    results = []
    for ws in workspaces_iter:
        if ws.latest_run and ws.latest_run.created_at and ws.latest_run.created_at >= since:
            results.append(ws)

    return results
