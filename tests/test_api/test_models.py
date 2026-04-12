"""Tests for model creation from API responses.

Tests the from_api_response() factory methods on Pydantic models.
"""

from datetime import datetime

from terrapyne.models.project import Project
from terrapyne.models.run import Run
from terrapyne.models.team_access import TeamProjectAccess
from terrapyne.models.workspace import Workspace


class TestWorkspaceModelParsing:
    """Test Workspace model creation from API responses."""

    def test_workspace_from_api_response(self):
        """Test creating Workspace from API response."""
        api_response = {
            "id": "ws-abc123",
            "type": "workspaces",
            "attributes": {
                "name": "my-workspace",
                "created-at": "2025-03-13T07:50:15.781Z",
                "terraform-version": "1.7.0",
                "execution-mode": "remote",
            },
        }

        workspace = Workspace.from_api_response(api_response)

        assert workspace.id == "ws-abc123"
        assert workspace.name == "my-workspace"
        assert workspace.terraform_version == "1.7.0"
        assert workspace.execution_mode == "remote"
        assert isinstance(workspace.created_at, datetime)

    def test_workspace_with_vcs(self):
        """Test Workspace with VCS configuration."""
        api_response = {
            "id": "ws-with-vcs",
            "type": "workspaces",
            "attributes": {
                "name": "vcs-workspace",
                "created-at": "2025-03-13T07:50:15.781Z",
                "terraform-version": "1.7.0",
                "execution-mode": "remote",
                "vcs-repo": {
                    "identifier": "myorg/my-repo",
                    "branch": "main",
                    "oauth-token-id": "ot-abc123",
                },
            },
        }

        workspace = Workspace.from_api_response(api_response)

        assert workspace.vcs_repo is not None
        assert workspace.vcs_repo.identifier == "myorg/my-repo"
        assert workspace.vcs_repo.branch == "main"

    def test_workspace_without_vcs(self):
        """Test Workspace without VCS configuration."""
        api_response = {
            "id": "ws-no-vcs",
            "type": "workspaces",
            "attributes": {
                "name": "local-workspace",
                "created-at": "2025-03-13T07:50:15.781Z",
                "terraform-version": "1.7.0",
                "execution-mode": "remote",
            },
        }

        workspace = Workspace.from_api_response(api_response)

        assert workspace.vcs_repo is None


class TestRunModelParsing:
    """Test Run model creation from API responses."""

    def test_run_from_api_response(self):
        """Test creating Run from API response."""
        api_response = {
            "id": "run-abc123",
            "type": "runs",
            "attributes": {
                "status": "applied",
                "created-at": "2025-03-13T08:00:00.000Z",
                "message": "Applied by user",
                "resource-additions": 3,
                "resource-changes": 2,
                "resource-destructions": 0,
            },
        }

        run = Run.from_api_response(api_response)

        assert run.id == "run-abc123"
        assert run.status == "applied"
        assert run.message == "Applied by user"
        assert run.resource_additions == 3
        assert run.resource_changes == 2
        assert run.resource_destructions == 0
        assert isinstance(run.created_at, datetime)

    def test_run_with_multiple_statuses(self):
        """Test parsing runs with different statuses."""
        statuses = ["planned", "confirmed", "applied", "discarded", "errored"]

        for status in statuses:
            api_response = {
                "id": f"run-{status}",
                "type": "runs",
                "attributes": {
                    "status": status,
                    "created-at": "2025-03-13T08:00:00.000Z",
                },
            }

            run = Run.from_api_response(api_response)
            assert run.status == status


class TestProjectModelParsing:
    """Test Project model creation from API responses."""

    def test_project_from_api_response(self):
        """Test creating Project from API response."""
        api_response = {
            "id": "prj-abc123",
            "type": "projects",
            "attributes": {
                "name": "my-infrastructure",
                "description": "Main infrastructure project",
                "created-at": "2025-03-13T07:50:15.781Z",
            },
        }

        project = Project.from_api_response(api_response)

        assert project.id == "prj-abc123"
        assert project.name == "my-infrastructure"
        assert project.description == "Main infrastructure project"
        assert isinstance(project.created_at, datetime)


class TestTeamAccessModelParsing:
    """Test TeamProjectAccess model creation from API responses."""

    def test_team_project_access_from_api_response(self):
        """Test creating TeamProjectAccess from API response."""
        api_response = {
            "id": "tpa-abc123",
            "type": "team-projects",
            "attributes": {
                "access": "admin",
            },
            "relationships": {
                "team": {"data": {"id": "team-1", "type": "teams"}},
                "project": {"data": {"id": "prj-1", "type": "projects"}},
            },
        }

        access = TeamProjectAccess.from_api_response(api_response)

        assert access.id == "tpa-abc123"
        assert access.access == "admin"

    def test_team_project_access_different_levels(self):
        """Test different access levels."""
        access_levels = ["admin", "maintain", "write", "read"]

        for level in access_levels:
            api_response = {
                "id": f"tpa-{level}",
                "type": "team-projects",
                "attributes": {
                    "access": level,
                },
                "relationships": {
                    "team": {"data": {"id": "team-1", "type": "teams"}},
                    "project": {"data": {"id": "prj-1", "type": "projects"}},
                },
            }

            access = TeamProjectAccess.from_api_response(api_response)
            assert access.access == level


class TestDatetimeParsing:
    """Test ISO 8601 datetime parsing from API responses."""

    def test_iso_datetime_with_z_suffix(self):
        """Test parsing ISO datetime with Z suffix."""
        from terrapyne.models.utils import parse_iso_datetime

        dt_str = "2025-03-13T07:50:15.781Z"
        dt = parse_iso_datetime(dt_str)

        assert dt is not None
        assert isinstance(dt, datetime)
        assert dt.year == 2025
        assert dt.month == 3
        assert dt.day == 13

    def test_iso_datetime_with_offset(self):
        """Test parsing ISO datetime with timezone offset."""
        from terrapyne.models.utils import parse_iso_datetime

        dt_str = "2025-03-13T07:50:15.781+00:00"
        dt = parse_iso_datetime(dt_str)

        assert dt is not None
        assert isinstance(dt, datetime)

    def test_iso_datetime_none_input(self):
        """Test parsing None datetime value."""
        from terrapyne.models.utils import parse_iso_datetime

        dt = parse_iso_datetime(None)
        assert dt is None

    def test_iso_datetime_empty_string(self):
        """Test parsing empty string datetime."""
        from terrapyne.models.utils import parse_iso_datetime

        dt = parse_iso_datetime("")
        assert dt is None
