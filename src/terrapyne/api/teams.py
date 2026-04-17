"""Teams API methods."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from terrapyne.api.client import TFCClient
from terrapyne.models.team import Team

if TYPE_CHECKING:
    from terrapyne.models.team_access import TeamProjectAccess, TeamProjectAccessComparison


class TeamsAPI:
    """Teams API operations."""

    def __init__(self, client: TFCClient):
        """Initialize teams API.

        Args:
            client: TFC API client
        """
        self.client = client

    def list_teams(
        self,
        organization: str | None = None,
        search: str | None = None,
        names: list[str] | None = None,
    ) -> tuple[Iterator[Team], int | None]:
        """List teams in an organization.

        Uses server-side filtering wherever possible to avoid paginating thousands of teams.

        Args:
            organization: Organization name (uses client default if not specified)
            search: Case-insensitive substring search via TFC `q=` parameter.
                    Preferred over client-side filtering for large orgs (1000+ teams).
            names: Exact name(s) to match via `filter[names]=` parameter.
                   Comma-separated list sent server-side; returns teams matching any name.

        Returns:
            Tuple of (iterator of Team instances, total count or None)

        Raises:
            TFCAPIError: If API request fails

        Examples:
            # Search by substring (server-side, efficient)
            teams, total = api.list_teams(search="platform")

            # Exact multi-name lookup (server-side, efficient)
            teams, total = api.list_teams(names=["platform-developer", "platform-viewer"])
        """
        org = self.client.get_organization(organization)
        path = f"/organizations/{org}/teams"

        params: dict[str, Any] = {}
        if search:
            # q= is case-insensitive substring search; vastly more efficient than
            # paginating all teams client-side in large orgs
            params["q"] = search
        if names:
            # filter[names] accepts comma-separated exact names; returns any matching
            params["filter[names]"] = ",".join(names)

        items_iterator, total_count = self.client.paginate_with_meta(path, params=params)

        def team_iterator() -> Iterator[Team]:
            for item in items_iterator:
                yield Team.from_api_response(item)

        return team_iterator(), total_count

    def get(self, team_id: str) -> Team:
        """Get team details by ID.

        Args:
            team_id: Team ID

        Returns:
            Team instance

        Raises:
            TFCAPIError: If team not found
        """
        path = f"/teams/{team_id}"
        response = self.client.get(path)
        return Team.from_api_response(response["data"])

    def create(
        self,
        organization: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> Team:
        """Create a new team.

        Args:
            organization: Organization name (uses client default if not specified)
            name: Team name
            description: Optional team description

        Returns:
            Created Team instance

        Raises:
            TFCAPIError: If creation fails
        """
        org = self.client.get_organization(organization)
        path = f"/organizations/{org}/teams"

        attributes: dict[str, Any] = {}
        if name:
            attributes["name"] = name
        if description is not None:
            attributes["description"] = description

        payload = {
            "data": {
                "type": "teams",
                "attributes": attributes,
            }
        }

        response = self.client.post(path, json_data=payload)
        return Team.from_api_response(response["data"])

    def update(
        self,
        team_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> Team:
        """Update a team.

        Args:
            team_id: Team ID
            name: New team name (optional)
            description: New team description (optional)

        Returns:
            Updated Team instance

        Raises:
            TFCAPIError: If update fails
        """
        path = f"/teams/{team_id}"

        attributes: dict[str, Any] = {}
        if name is not None:
            attributes["name"] = name
        if description is not None:
            attributes["description"] = description

        payload = {
            "data": {
                "type": "teams",
                "attributes": attributes,
            }
        }

        response = self.client.patch(path, json_data=payload)
        return Team.from_api_response(response["data"])

    def delete(self, team_id: str) -> None:
        """Delete a team.

        Args:
            team_id: Team ID

        Raises:
            TFCAPIError: If deletion fails
        """
        path = f"/teams/{team_id}"
        self.client.delete(path)

    def list_members(self, team_id: str) -> tuple[list[dict[str, Any]], int | None]:
        """List members in a team.

        Args:
            team_id: Team ID

        Returns:
            Tuple of (list of user dicts, total count or None)

        Raises:
            TFCAPIError: If API request fails
        """
        path = f"/teams/{team_id}/relationships/users"

        items_iterator, total_count = self.client.paginate_with_meta(path)
        members = list(items_iterator)

        return members, total_count

    def add_member(self, team_id: str, user_id: str) -> None:
        """Add a user to a team.

        Args:
            team_id: Team ID
            user_id: User ID

        Raises:
            TFCAPIError: If add fails (user already in team, etc.)
        """
        path = f"/teams/{team_id}/relationships/users"

        payload = {
            "data": [
                {
                    "type": "users",
                    "id": user_id,
                }
            ]
        }

        self.client.post(path, json_data=payload)

    def remove_member(self, team_id: str, user_id: str) -> None:
        """Remove a user from a team.

        Args:
            team_id: Team ID
            user_id: User ID

        Raises:
            TFCAPIError: If removal fails (user not in team, etc.)
        """
        path = f"/teams/{team_id}/relationships/users"

        payload = {
            "data": [
                {
                    "type": "users",
                    "id": user_id,
                }
            ]
        }

        # Use DELETE with JSON body
        self.client.delete(path, json_data=payload)

    def get_project_access(self, project_id: str, team_id: str) -> TeamProjectAccess:
        """Get a team's access record for a specific project.

        Args:
            project_id: Project ID
            team_id: Team ID

        Returns:
            TeamProjectAccess instance

        Raises:
            ValueError: If no access record found for this team/project combination
        """
        from terrapyne.models.team_access import TeamProjectAccess

        path = "/team-projects"
        params = {"filter[project][id]": project_id}

        for item in self.client.paginate(path, params=params):
            access = TeamProjectAccess.from_api_response(item)
            if access.team_id == team_id:
                return access

        raise ValueError(
            f"No project access record found for team '{team_id}' in project '{project_id}'"
        )

    def set_project_access(
        self,
        project_id: str,
        team_id: str,
        access: str,
    ) -> TeamProjectAccess:
        """Update a team's access level on a project.

        Finds the existing team-project access record and PATCHes it to the
        desired named access level. Named levels (admin, maintain, write, read)
        cause TFC to expand the full workspace_access permissions server-side.

        Args:
            project_id: Project ID
            team_id: Team ID
            access: Access level — one of: admin | maintain | write | read

        Returns:
            Updated TeamProjectAccess instance

        Raises:
            ValueError: If access level invalid or no existing record found
            TFCAPIError: If PATCH fails
        """
        from terrapyne.models.team_access import TeamProjectAccess

        valid_levels = {"admin", "maintain", "write", "read"}
        if access not in valid_levels:
            raise ValueError(f"Invalid access level '{access}'. Must be one of: {valid_levels}")

        # Find existing record ID
        existing = self.get_project_access(project_id, team_id)

        path = f"/team-projects/{existing.id}"
        payload = {
            "data": {
                "type": "team-projects",
                "attributes": {"access": access},
            }
        }

        response = self.client.patch(path, json_data=payload)
        return TeamProjectAccess.from_api_response(response["data"])

    def compare_project_access(
        self,
        project_id_a: str,
        team_id_a: str,
        project_id_b: str,
        team_id_b: str,
    ) -> TeamProjectAccessComparison:
        """Compare project access permissions between two teams.

        Fetches both access records and produces a structured comparison
        including whether they are identical and a field-level diff.

        Args:
            project_id_a: Project ID for team A (reference/gold-standard)
            team_id_a: Team ID for team A
            project_id_b: Project ID for team B (target)
            team_id_b: Team ID for team B

        Returns:
            TeamProjectAccessComparison with identical flag and diffs
        """
        from terrapyne.models.team_access import TeamProjectAccessComparison

        access_a = self.get_project_access(project_id_a, team_id_a)
        access_b = self.get_project_access(project_id_b, team_id_b)

        return TeamProjectAccessComparison.compare(access_a, access_b)
