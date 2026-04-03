"""VCS API methods."""

from __future__ import annotations

from collections import defaultdict

from terrapyne.api.client import TFCClient
from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.models.vcs import VCSConnection
from terrapyne.models.workspace import Workspace


class VCSAPI:
    """VCS API operations."""

    def __init__(self, client: TFCClient):
        """Initialize VCS API.

        Args:
            client: TFC API client
        """
        self.client = client

    def get_workspace_vcs(self, workspace_id: str) -> VCSConnection | None:
        """Get VCS connection for workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            VCSConnection instance or None if workspace has no VCS connection

        Raises:
            httpx.HTTPStatusError: If workspace not found
        """
        response = self.client.get(f"/workspaces/{workspace_id}")
        workspace_data = response["data"]
        vcs_data = workspace_data.get("attributes", {}).get("vcs-repo")

        if not vcs_data:
            return None

        return VCSConnection.from_api_response(vcs_data)

    def update_workspace_branch(
        self,
        workspace_id: str,
        branch: str,
        oauth_token_id: str,
    ) -> Workspace:
        """Update VCS branch for workspace.

        Preserves all other VCS settings (repo, working-dir, submodules).

        Args:
            workspace_id: Workspace ID
            branch: New branch name
            oauth_token_id: OAuth token ID from environment variable

        Returns:
            Updated Workspace instance

        Raises:
            ValueError: If workspace has no VCS connection
            httpx.HTTPStatusError: If API request fails
        """
        # Get current workspace config
        current_vcs = self.get_workspace_vcs(workspace_id)
        if not current_vcs:
            raise ValueError(f"Workspace {workspace_id} has no VCS connection")

        # Build update payload preserving existing settings
        vcs_payload: dict[str, str | bool] = {
            "identifier": current_vcs.identifier,
            "oauth-token-id": oauth_token_id,
            "branch": branch,
            "ingress-submodules": current_vcs.ingress_submodules,
        }

        # Add optional fields if they exist
        if current_vcs.working_directory:
            vcs_payload["working-directory"] = current_vcs.working_directory

        payload = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "vcs-repo": vcs_payload,
                },
            }
        }

        response = self.client.patch(f"/workspaces/{workspace_id}", json_data=payload)
        return Workspace.from_api_response(response["data"])

    def list_repositories(self, organization: str) -> list[dict]:
        """Discover GitHub repositories connected to TFC workspaces.

        Args:
            organization: Organization name

        Returns:
            List of dicts with:
            - identifier: Repository identifier (owner/repo)
            - url: GitHub URL
            - workspaces: List of workspace names using this repo

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        workspaces_api = WorkspaceAPI(self.client)
        workspaces_iter, _ = workspaces_api.list(organization)
        workspaces = list(workspaces_iter)

        # Group workspaces by repository
        repos: dict[str, dict] = defaultdict(lambda: {"workspaces": []})

        for workspace in workspaces:
            vcs = self.get_workspace_vcs(workspace.id)
            if vcs and vcs.service_provider == "github":
                identifier = vcs.identifier
                if identifier not in repos:
                    repos[identifier] = {
                        "identifier": identifier,
                        "url": vcs.github_url,
                        "workspaces": [],
                    }
                repos[identifier]["workspaces"].append(workspace.name)

        return sorted(repos.values(), key=lambda x: x["identifier"])
