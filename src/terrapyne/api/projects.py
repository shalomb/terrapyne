"""Project API methods."""

from __future__ import annotations

import builtins
from collections.abc import Iterator
from typing import TYPE_CHECKING

from terrapyne.api.client import TFCClient
from terrapyne.models.project import Project

if TYPE_CHECKING:
    from terrapyne.models.team_access import TeamProjectAccess


class ProjectAPI:
    """Project API operations."""

    def __init__(self, client: TFCClient):
        """Initialize project API.

        Args:
            client: TFC API client
        """
        self.client = client

    def list(
        self, organization: str | None = None, search: str | None = None
    ) -> tuple[Iterator[Project], int | None]:
        """List projects in an organization.

        Args:
            organization: Organization name (uses client default if not specified)
            search: Search pattern for project names (supports wildcards like *-MAN, 10234-*)

        Returns:
            Tuple of (iterator of Project instances, total count or None)
        """
        org = self.client.get_organization(organization)
        path = f"/organizations/{org}/projects"

        params = {}
        if search:
            # Strip wildcards for API - TFC uses 'q' for substring search
            search_term = search.replace("*", "")
            params["q"] = search_term

        items_iterator, total_count = self.client.paginate_with_meta(path, params=params)

        def project_iterator() -> Iterator[Project]:
            for item in items_iterator:
                yield Project.from_api_response(item)

        return project_iterator(), total_count

    def get_by_name(self, name: str, organization: str | None = None) -> Project:
        """Get project by name.

        Args:
            name: Project name
            organization: Organization name (uses client default if not specified)

        Returns:
            Project instance

        Raises:
            ValueError: If project not found
        """
        org = self.client.get_organization(organization)

        # Search for project by name using the list API with search
        projects_iter, _ = self.list(org, search=name)

        # Find exact match (case-insensitive search returns partial matches)
        for project in projects_iter:
            if project.name == name:
                return project

        # If not found, raise error
        raise ValueError(f"Project '{name}' not found in organization '{org}'")

    def get_by_id(self, project_id: str) -> Project:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project instance

        Raises:
            httpx.HTTPStatusError: If project not found
        """
        path = f"/projects/{project_id}"

        response = self.client.get(path)
        return Project.from_api_response(response["data"])

    def get_workspace_counts(self, organization: str | None = None) -> dict[str, int]:
        """Get actual workspace counts per project.

        Args:
            organization: Organization name (uses client default if not specified)

        Returns:
            Dict mapping project_id -> workspace count
        """
        from terrapyne.api.workspaces import WorkspaceAPI

        org = self.client.get_organization(organization)
        workspace_api = WorkspaceAPI(self.client)

        # Fetch all workspaces and count by project_id
        workspaces_iter, _ = workspace_api.list(org)
        workspace_counts: dict[str, int] = {}

        for ws in workspaces_iter:
            if ws.project_id:
                workspace_counts[ws.project_id] = workspace_counts.get(ws.project_id, 0) + 1

        return workspace_counts

    def list_team_access(self, project_id: str) -> builtins.list[TeamProjectAccess]:
        """List team access for a project.

        Args:
            project_id: Project ID

        Returns:
            List of TeamProjectAccess instances with team names populated
        """
        from terrapyne.api.teams import TeamsAPI
        from terrapyne.models.team_access import TeamProjectAccess

        path = "/team-projects"
        params = {"filter[project][id]": project_id}

        # Fetch team access records
        team_access_list = []
        for item in self.client.paginate(path, params=params):
            team_access_list.append(TeamProjectAccess.from_api_response(item))

        # Fetch team names for each team ID
        teams_api = TeamsAPI(self.client)
        for access in team_access_list:
            try:
                team = teams_api.get(access.team_id)
                access.team_name = team.name
            except Exception:
                # If team lookup fails, keep team_name as None
                pass

        return team_access_list
