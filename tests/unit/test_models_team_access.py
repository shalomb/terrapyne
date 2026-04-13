"""Unit tests for team access models."""

from terrapyne.models.team_access import (
    AccessDiff,
    ProjectAccess,
    TeamProjectAccess,
    TeamProjectAccessComparison,
    WorkspaceAccess,
)


class TestProjectAccess:
    """Test ProjectAccess model."""

    def test_project_access_defaults(self):
        """Test ProjectAccess default values."""
        access = ProjectAccess()
        assert access.settings == "read"
        assert access.teams == "none"

    def test_project_access_custom(self):
        """Test ProjectAccess with custom values."""
        access = ProjectAccess(settings="delete", teams="manage")
        assert access.settings == "delete"
        assert access.teams == "manage"


class TestWorkspaceAccess:
    """Test WorkspaceAccess model."""

    def test_workspace_access_defaults(self):
        """Test WorkspaceAccess default values."""
        access = WorkspaceAccess()
        assert access.create is False
        assert access.locking is False
        assert access.runs == "read"
        assert access.variables == "read"

    def test_workspace_access_custom(self):
        """Test WorkspaceAccess with custom values."""
        access = WorkspaceAccess(
            create=True,
            locking=True,
            runs="apply",
            variables="write",
        )
        assert access.create is True
        assert access.locking is True
        assert access.runs == "apply"
        assert access.variables == "write"


class TestTeamProjectAccess:
    """Test TeamProjectAccess model."""

    def test_from_api_response_full(self):
        """Test creating TeamProjectAccess from API response with all fields."""
        api_response = {
            "id": "tpa-123",
            "attributes": {
                "access": "admin",
                "project-access": {"settings": "delete", "teams": "manage"},
                "workspace-access": {"runs": "apply", "variables": "write"},
            },
            "relationships": {
                "team": {"data": {"id": "team-456"}},
                "project": {"data": {"id": "proj-789"}},
            },
        }

        access = TeamProjectAccess.from_api_response(api_response)

        assert access.id == "tpa-123"
        assert access.access == "admin"
        assert access.team_id == "team-456"
        assert access.project_id == "proj-789"
        assert access.project_access is not None
        assert access.project_access.settings == "delete"
        assert access.workspace_access is not None
        assert access.workspace_access.runs == "apply"

    def test_from_api_response_minimal(self):
        """Test creating TeamProjectAccess without project/workspace access."""
        api_response = {
            "id": "tpa-min",
            "attributes": {
                "access": "read",
            },
            "relationships": {
                "team": {"data": {"id": "team-min"}},
                "project": {"data": {"id": "proj-min"}},
            },
        }

        access = TeamProjectAccess.from_api_response(api_response)

        assert access.id == "tpa-min"
        assert access.access == "read"
        assert access.project_access is None
        assert access.workspace_access is None

    def test_from_api_response_missing_relationships(self):
        """Test creating TeamProjectAccess with missing relationships."""
        api_response = {
            "id": "tpa-partial",
            "attributes": {"access": "write"},
            "relationships": {},
        }

        access = TeamProjectAccess.from_api_response(api_response)

        assert access.id == "tpa-partial"
        assert access.team_id == ""
        assert access.project_id == ""


class TestAccessDiff:
    """Test AccessDiff model."""

    def test_access_diff(self):
        """Test AccessDiff creation."""
        diff = AccessDiff(
            field="access",
            value_a="read",
            value_b="write",
        )

        assert diff.field == "access"
        assert diff.value_a == "read"
        assert diff.value_b == "write"


class TestTeamProjectAccessComparison:
    """Test TeamProjectAccessComparison comparison logic."""

    def test_identical_access(self):
        """Test comparison of identical access records."""
        access_a = TeamProjectAccess(
            id="a",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
        )
        access_b = TeamProjectAccess(
            id="b",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
        )

        comparison = TeamProjectAccessComparison.compare(access_a, access_b)

        assert comparison.identical is True
        assert len(comparison.diffs) == 0

    def test_different_access_level(self):
        """Test comparison with different access levels."""
        access_a = TeamProjectAccess(
            id="a",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
        )
        access_b = TeamProjectAccess(
            id="b",
            access="read",
            team_id="team-1",
            project_id="proj-1",
        )

        comparison = TeamProjectAccessComparison.compare(access_a, access_b)

        assert comparison.identical is False
        assert len(comparison.diffs) == 1
        assert comparison.diffs[0].field == "access"

    def test_different_project_access(self):
        """Test comparison with different project access."""
        access_a = TeamProjectAccess(
            id="a",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
            project_access=ProjectAccess(settings="delete", teams="manage"),
        )
        access_b = TeamProjectAccess(
            id="b",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
            project_access=ProjectAccess(settings="read", teams="none"),
        )

        comparison = TeamProjectAccessComparison.compare(access_a, access_b)

        assert comparison.identical is False
        diffs = [d.field for d in comparison.diffs]
        assert "project_access.settings" in diffs
        assert "project_access.teams" in diffs

    def test_project_access_one_none(self):
        """Test comparison when one has project_access and other doesn't."""
        access_a = TeamProjectAccess(
            id="a",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
            project_access=ProjectAccess(),
        )
        access_b = TeamProjectAccess(
            id="b",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
            project_access=None,
        )

        comparison = TeamProjectAccessComparison.compare(access_a, access_b)

        assert comparison.identical is False
        assert len(comparison.diffs) == 1
        assert comparison.diffs[0].field == "project_access"

    def test_different_workspace_access(self):
        """Test comparison with different workspace access."""
        access_a = TeamProjectAccess(
            id="a",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
            workspace_access=WorkspaceAccess(runs="apply", variables="write"),
        )
        access_b = TeamProjectAccess(
            id="b",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
            workspace_access=WorkspaceAccess(runs="read", variables="read"),
        )

        comparison = TeamProjectAccessComparison.compare(access_a, access_b)

        assert comparison.identical is False
        diffs = [d.field for d in comparison.diffs]
        assert "workspace_access.runs" in diffs
        assert "workspace_access.variables" in diffs

    def test_workspace_access_one_none(self):
        """Test comparison when one has workspace_access and other doesn't."""
        access_a = TeamProjectAccess(
            id="a",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
            workspace_access=WorkspaceAccess(),
        )
        access_b = TeamProjectAccess(
            id="b",
            access="admin",
            team_id="team-1",
            project_id="proj-1",
            workspace_access=None,
        )

        comparison = TeamProjectAccessComparison.compare(access_a, access_b)

        assert comparison.identical is False
        assert len(comparison.diffs) == 1
        assert comparison.diffs[0].field == "workspace_access"
