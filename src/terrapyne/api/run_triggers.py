"""Run Triggers API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from terrapyne.models.run_trigger import RunTrigger

if TYPE_CHECKING:
    from terrapyne.api.client import TFCClient


class RunTriggersAPI:
    """Run Triggers API operations."""

    def __init__(self, client: "TFCClient"):
        self.client = client

    def list(self, workspace_id: str) -> list[RunTrigger]:
        """List upstream run trigger sources for a workspace.

        Args:
            workspace_id: The downstream workspace ID

        Returns:
            List of RunTrigger instances
        """
        path = f"/workspaces/{workspace_id}/run-triggers"
        response = self.client.get(
            path,
            params={"filter[run-trigger][type]": "inbound", "include": "source-workspace"},
        )
        included = response.get("included", [])
        return [
            RunTrigger.from_api_response(item, included=included)
            for item in response.get("data", [])
        ]

    def add(self, workspace_id: str, source_workspace_id: str) -> RunTrigger:
        """Add an upstream run trigger to a workspace.

        Args:
            workspace_id: The downstream workspace ID
            source_workspace_id: The upstream (source) workspace ID

        Returns:
            Created RunTrigger instance
        """
        path = f"/workspaces/{workspace_id}/run-triggers"
        payload: dict[str, Any] = {
            "data": {
                "type": "run-triggers",
                "relationships": {
                    "sourceable": {"data": {"id": source_workspace_id, "type": "workspaces"}}
                },
            }
        }
        response = self.client.post(path, json_data=payload)
        included = response.get("included", [])
        return RunTrigger.from_api_response(response["data"], included=included)

    def remove(self, run_trigger_id: str) -> None:
        """Remove a run trigger.

        Args:
            run_trigger_id: The run trigger ID to delete
        """
        self.client.delete(f"/run-triggers/{run_trigger_id}")
