"""Terraform Cloud State Versions API."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from typing import Any

from terrapyne.models.state_version import StateVersion, StateVersionOutput


class StateVersionsAPI:
    """State Versions API operations."""

    def __init__(self, client: Any):
        self.client = client

    def list(  # noqa: A003
        self,
        workspace_id: str | None = None,
        organization: str | None = None,
        workspace_name: str | None = None,
        limit: int = 20,
    ) -> tuple[builtins.list[StateVersion], int | None]:
        """List state versions for a workspace.

        Can filter by workspace ID or by org+name. The TFC API supports both.

        Args:
            workspace_id: Workspace ID (used if org/name not provided)
            organization: Organization name (for name-based filtering)
            workspace_name: Workspace name (for name-based filtering)
            limit: Maximum versions to return

        Returns:
            Tuple of (list of StateVersion most recent first, total count or None)
        """
        path = "/state-versions"
        params: dict[str, Any] = {}

        if organization and workspace_name:
            params["filter[organization][name]"] = organization
            params["filter[workspace][name]"] = workspace_name
        else:
            params["filter[workspace][id]"] = workspace_id

        items_iter, total_count = self.client.paginate_with_meta(path, params=params)

        versions = []
        for item in items_iter:
            versions.append(StateVersion.from_api_response(item))
            if len(versions) >= limit:
                break

        return versions, total_count

    def get(self, state_version_id: str) -> StateVersion:
        """Get a state version by ID."""
        path = f"/state-versions/{state_version_id}"
        response = self.client.get(path)
        return StateVersion.from_api_response(response["data"])

    def get_current(self, workspace_id: str) -> StateVersion:
        """Get the current (latest) state version for a workspace."""
        path = f"/workspaces/{workspace_id}/current-state-version"
        response = self.client.get(path)
        return StateVersion.from_api_response(response["data"])

    def download(self, state_version_id: str) -> dict[str, Any]:
        """Download raw state JSON for a state version.

        Follows the signed hosted-state-download-url.
        """
        sv = self.get(state_version_id)
        if not sv.download_url:
            raise ValueError(f"State version {state_version_id} has no download URL")
        response = self.client.client.get(sv.download_url)
        response.raise_for_status()
        return response.json()

    def download_from_url(self, download_url: str) -> dict[str, Any]:
        """Download raw state JSON from a signed URL directly."""
        response = self.client.client.get(download_url)
        response.raise_for_status()
        return response.json()

    def list_outputs(self, state_version_id: str) -> builtins.list[StateVersionOutput]:
        """List outputs for a state version without downloading full state."""
        path = f"/state-versions/{state_version_id}/outputs"
        outputs = []
        for item in self.client.paginate(path):
            attrs = item.get("attributes", {})
            outputs.append(
                StateVersionOutput(
                    name=attrs.get("name", ""),
                    value=attrs.get("value"),
                    type=attrs.get("type"),
                    sensitive=attrs.get("sensitive", False),
                )
            )
        return outputs

    def find_version_before(self, workspace_id: str, before: datetime) -> StateVersion | None:
        """Find the last state version created before a given datetime.

        Walks state versions (most recent first) and returns the first one
        with created_at < before. Early exits — does not fetch all versions.

        Both sides are normalized to UTC to avoid naive/aware comparison errors.
        """

        # Ensure 'before' is timezone-aware (UTC)
        if before.tzinfo is None:
            before = before.replace(tzinfo=UTC)

        path = "/state-versions"
        params = {"filter[workspace][id]": workspace_id}

        for item in self.client.paginate(path, params=params):
            sv = StateVersion.from_api_response(item)
            if not sv.created_at:
                continue
            # Ensure created_at is timezone-aware (UTC)
            created = sv.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if created < before:
                return sv

        return None
