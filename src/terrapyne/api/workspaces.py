"""Workspace API methods."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from terrapyne.api.client import TFCClient
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.workspace import Workspace


class WorkspaceAPI:
    """Workspace API operations."""

    def __init__(self, client: TFCClient):
        """Initialize workspace API.

        Args:
            client: TFC API client
        """
        self.client = client

    def list(
        self,
        organization: str | None = None,
        search: str | None = None,
        project_id: str | None = None,
        include: str | None = None,
        current_run_status: str | None = None,
    ) -> tuple[Iterator[Workspace], int | None]:
        """List workspaces in an organization.

        Args:
            organization: Organization name (uses client default if not specified)
            search: Search pattern for workspace names
            project_id: Filter by project ID
            include: Resources to include
            current_run_status: Filter by the status of each workspace's current run
                (e.g. "errored"). Automatically adds "latest-run" to includes so that
                the embedded run is available without a second API call.

        Returns:
            Tuple of (iterator of Workspace instances, total count or None)
        """
        org = self.client.get_organization(organization)
        path = f"/organizations/{org}/workspaces"

        params: dict[str, Any] = {}

        # Build include list, ensuring latest-run is present when filtering by run status.
        includes = set(include.split(",") if include else [])
        if current_run_status:
            includes.add("latest-run")
        if includes:
            params["include"] = ",".join(sorted(includes))

        if search:
            if "*" in search:
                params["search[wildcard-name]"] = search
            else:
                params["search[name]"] = search
        if project_id:
            params["filter[project][id]"] = project_id
        if current_run_status:
            params["filter[current-run][status]"] = current_run_status

        items_iterator, total_count = self.client.paginate_with_meta(path, params=params)

        def workspace_iterator() -> Iterator[Workspace]:
            for item in items_iterator:
                yield Workspace.from_api_response(item, included=items_iterator.included)

        return workspace_iterator(), total_count

    def get(
        self,
        workspace_name: str,
        organization: str | None = None,
        include: str | None = "project",
    ) -> Workspace:
        """Get workspace by name.

        Args:
            workspace_name: Workspace name
            organization: Organization name (uses client default if not specified)
            include: Resources to include (default: project)

        Returns:
            Workspace instance

        Raises:
            TFCAPIError: If workspace not found
        """
        org = self.client.get_organization(organization)
        path = f"/organizations/{org}/workspaces/{workspace_name}"

        params = {}
        if include:
            params["include"] = include

        response = self.client.get(path, params=params)
        return Workspace.from_api_response(response["data"], response.get("included", []))

    def get_by_id(self, workspace_id: str, include: str | None = "project") -> Workspace:
        """Get workspace by ID.

        Args:
            workspace_id: Workspace ID
            include: Resources to include (default: project)

        Returns:
            Workspace instance

        Raises:
            TFCAPIError: If workspace not found
        """
        path = f"/workspaces/{workspace_id}"

        params = {}
        if include:
            params["include"] = include

        response = self.client.get(path, params=params)
        return Workspace.from_api_response(response["data"], response.get("included", []))

    def get_variables(self, workspace_id: str) -> list[WorkspaceVariable]:  # type: ignore[valid-type]
        """Get variables for a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of WorkspaceVariable instances

        Raises:
            TFCAPIError: If API request fails
        """
        path = f"/workspaces/{workspace_id}/vars"

        variables = []
        for item in self.client.paginate(path):
            variables.append(WorkspaceVariable.from_api_response(item))

        # Sort variables: terraform vars first, then env vars, alphabetically within each
        return sorted(variables, key=lambda v: (0 if v.is_terraform_var else 1, v.key.lower()))

    def create_variable(
        self,
        workspace_id: str,
        key: str,
        value: str,
        category: str = "terraform",
        hcl: bool = False,
        sensitive: bool = False,
        description: str | None = None,
    ) -> WorkspaceVariable:
        """Create a new variable in a workspace.

        Args:
            workspace_id: Workspace ID
            key: Variable name/key
            value: Variable value
            category: Variable category - "terraform" or "env" (default: "terraform")
            hcl: Whether value is HCL encoded (default: False)
            sensitive: Whether value is sensitive/masked (default: False)
            description: Optional variable description

        Returns:
            Created WorkspaceVariable instance

        Raises:
            TFCAPIError: If API request fails
        """
        path = "/vars"

        attributes: dict[str, Any] = {
            "key": key,
            "value": value,
            "category": category,
            "hcl": hcl,
            "sensitive": sensitive,
        }
        if description is not None:
            attributes["description"] = description

        payload = {
            "data": {
                "type": "vars",
                "attributes": attributes,
                "relationships": {
                    "workspace": {"data": {"type": "workspaces", "id": workspace_id}}
                },
            }
        }

        response = self.client.post(path, json_data=payload)
        return WorkspaceVariable.from_api_response(response["data"])

    def update_variable(
        self,
        variable_id: str,
        key: str | None = None,
        value: str | None = None,
        hcl: bool | None = None,
        sensitive: bool | None = None,
        description: str | None = None,
    ) -> WorkspaceVariable:
        """Update an existing variable.

        Args:
            variable_id: Variable ID to update
            key: New variable name (optional)
            value: New variable value (optional)
            hcl: Update HCL encoding flag (optional)
            sensitive: Update sensitive flag (optional)
            description: Update variable description (optional)

        Returns:
            Updated WorkspaceVariable instance

        Raises:
            TFCAPIError: If API request fails
        """
        path = f"/vars/{variable_id}"

        # Build attributes dict with only provided values
        attributes: dict[str, Any] = {}
        if key is not None:
            attributes["key"] = key
        if value is not None:
            attributes["value"] = value
        if hcl is not None:
            attributes["hcl"] = hcl
        if sensitive is not None:
            attributes["sensitive"] = sensitive
        if description is not None:
            attributes["description"] = description

        payload = {
            "data": {
                "type": "vars",
                "attributes": attributes,
            }
        }

        response = self.client.patch(path, json_data=payload)
        return WorkspaceVariable.from_api_response(response["data"])

    def delete_variable(self, workspace_id: str, variable_id: str) -> None:
        """Delete a workspace variable.

        Args:
            workspace_id: Workspace ID (for logging/context)
            variable_id: Variable ID to delete

        Raises:
            TFCAPIError: If deletion fails
        """
        path = f"/vars/{variable_id}"
        self.client.delete(path)

    def create(
        self,
        name: str,
        organization: str | None = None,
        project_id: str | None = None,
        terraform_version: str | None = None,
        execution_mode: str | None = None,
        working_directory: str | None = None,
        vcs_repo: dict[str, str] | None = None,
    ) -> Workspace:
        """Create a new workspace.

        Args:
            name: Workspace name
            organization: Organization name (uses client default if not specified)
            project_id: Project ID to associate workspace with
            terraform_version: Terraform version to use
            execution_mode: Execution mode (remote, local, agent)
            working_directory: Working directory within VCS repo
            vcs_repo: VCS repository config dict with keys: identifier, oauth-token-id, branch

        Returns:
            Created Workspace instance

        Raises:
            TFCAPIError: If creation fails (e.g., 409 if workspace already exists)
        """
        org = self.client.get_organization(organization)
        path = f"/organizations/{org}/workspaces"

        attributes: dict[str, Any] = {"name": name}
        if terraform_version:
            attributes["terraform-version"] = terraform_version
        if execution_mode:
            attributes["execution-mode"] = execution_mode
        if working_directory:
            attributes["working-directory"] = working_directory
        if vcs_repo:
            attributes["vcs-repo"] = vcs_repo

        payload: dict[str, Any] = {"data": {"type": "workspaces", "attributes": attributes}}

        if project_id:
            payload["data"]["relationships"] = {
                "project": {"data": {"type": "projects", "id": project_id}}
            }

        response = self.client.post(path, json_data=payload)
        return Workspace.from_api_response(response["data"])

    def delete(self, workspace_id: str) -> None:
        """Delete a workspace by ID.

        Args:
            workspace_id: Workspace ID to delete

        Raises:
            TFCAPIError: If deletion fails
        """
        path = f"/workspaces/{workspace_id}"
        self.client.delete(path)
