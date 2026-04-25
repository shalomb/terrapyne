"""Tests for ProjectAPI."""

from unittest.mock import MagicMock, patch

import pytest

from terrapyne.api.client import TFCClient
from terrapyne.api.projects import ProjectAPI


@pytest.fixture
def mock_client():
    return MagicMock(spec=TFCClient)


@pytest.fixture
def project_api(mock_client):
    return ProjectAPI(mock_client)


def test_list_projects_basic(project_api, mock_client):
    """Test listing projects."""
    mock_client.get_organization.return_value = "test-org"
    mock_client.paginate_with_meta.return_value = (
        iter([{"id": "prj-1", "type": "projects", "attributes": {"name": "p1"}}]),
        1,
    )

    projects_iter, total = project_api.list()

    projects = list(projects_iter)
    assert len(projects) == 1
    assert projects[0].id == "prj-1"
    assert total == 1
    mock_client.paginate_with_meta.assert_called_once_with(
        "/organizations/test-org/projects", params={}
    )


def test_list_projects_with_search_exact(project_api, mock_client):
    """Test listing projects with exact name search."""
    mock_client.get_organization.return_value = "test-org"
    mock_client.paginate_with_meta.return_value = (iter([]), 0)

    project_api.list(search="exact-name")

    mock_client.paginate_with_meta.assert_called_once_with(
        "/organizations/test-org/projects", params={"filter[names]": "exact-name"}
    )


def test_list_projects_with_search_wildcard(project_api, mock_client):
    """Test listing projects with wildcard search."""
    mock_client.get_organization.return_value = "test-org"
    mock_client.paginate_with_meta.return_value = (iter([]), 0)

    project_api.list(search="wild*card")

    mock_client.paginate_with_meta.assert_called_once_with(
        "/organizations/test-org/projects", params={"q": "wildcard"}
    )


def test_get_project_by_name_found(project_api, mock_client):
    """Test get_by_name when project exists."""
    mock_client.get_organization.return_value = "test-org"
    prj_data = {"id": "prj-123", "type": "projects", "attributes": {"name": "target-project"}}
    mock_client.paginate_with_meta.return_value = (iter([prj_data]), 1)

    project = project_api.get_by_name("target-project")

    assert project.id == "prj-123"
    assert project.name == "target-project"


def test_get_project_by_name_not_found(project_api, mock_client):
    """Test get_by_name when project does not exist."""
    mock_client.get_organization.return_value = "test-org"
    mock_client.paginate_with_meta.return_value = (iter([]), 0)

    with pytest.raises(ValueError, match="Project 'missing' not found"):
        project_api.get_by_name("missing")


def test_get_project_by_id(project_api, mock_client):
    """Test get_by_id."""
    prj_data = {"data": {"id": "prj-123", "type": "projects", "attributes": {"name": "p1"}}}
    mock_client.get.return_value = prj_data

    project = project_api.get_by_id("prj-123")

    assert project.id == "prj-123"
    mock_client.get.assert_called_once_with("/projects/prj-123")


def test_get_workspace_counts(project_api, mock_client):
    """Test aggregating workspace counts per project."""
    mock_client.get_organization.return_value = "test-org"

    # Mock workspaces list
    ws1 = MagicMock()
    ws1.project_id = "prj-1"
    ws2 = MagicMock()
    ws2.project_id = "prj-1"
    ws3 = MagicMock()
    ws3.project_id = "prj-2"
    ws4 = MagicMock()
    ws4.project_id = None  # Should be ignored

    # Need to mock WorkspaceAPI.list which is used inside get_workspace_counts
    with patch("terrapyne.api.workspaces.WorkspaceAPI.list") as mock_ws_list:
        mock_ws_list.return_value = (iter([ws1, ws2, ws3, ws4]), 4)

        counts = project_api.get_workspace_counts()

        assert counts == {"prj-1": 2, "prj-2": 1}


def test_list_team_access(project_api, mock_client):
    """Test listing team access for a project."""
    # 1. Mock paginate for team-projects
    access_data = [
        {
            "id": "tpa-1",
            "type": "team-projects",
            "attributes": {"access": "admin"},
            "relationships": {
                "team": {"data": {"id": "team-1", "type": "teams"}},
                "project": {"data": {"id": "prj-1", "type": "projects"}},
            },
        }
    ]
    mock_client.paginate.return_value = iter(access_data)

    # 2. Mock TeamsAPI.get for team name enrichment
    with patch("terrapyne.api.teams.TeamsAPI.get") as mock_team_get:
        team_mock = MagicMock()
        team_mock.name = "Platform Team"
        mock_team_get.return_value = team_mock

        access_list = project_api.list_team_access("prj-1")

        assert len(access_list) == 1
        assert access_list[0].access == "admin"
        assert access_list[0].team_name == "Platform Team"
        mock_team_get.assert_called_once_with("team-1")


def test_list_team_access_enrichment_failure(project_api, mock_client):
    """Test team access listing when team name enrichment fails."""
    access_data = [
        {
            "id": "tpa-1",
            "type": "team-projects",
            "attributes": {"access": "admin"},
            "relationships": {
                "team": {"data": {"id": "team-1", "type": "teams"}},
            },
        }
    ]
    mock_client.paginate.return_value = iter(access_data)

    with patch("terrapyne.api.teams.TeamsAPI.get") as mock_team_get:
        mock_team_get.side_effect = Exception("API Error")

        access_list = project_api.list_team_access("prj-1")

        assert len(access_list) == 1
        assert access_list[0].team_name is None  # Enrichment failed but didn't crash
