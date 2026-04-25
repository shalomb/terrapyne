"""Tests for VCSAPI."""

from unittest.mock import MagicMock, patch

import pytest

from terrapyne.api.client import TFCClient
from terrapyne.api.vcs import VCSAPI
from terrapyne.models.vcs import VCSConnection


@pytest.fixture
def mock_client():
    return MagicMock(spec=TFCClient)


@pytest.fixture
def vcs_api(mock_client):
    return VCSAPI(mock_client)


def test_get_workspace_vcs_found(vcs_api, mock_client):
    """Test getting VCS for workspace when it exists."""
    ws_data = {
        "data": {
            "id": "ws-123",
            "attributes": {
                "vcs-repo": {
                    "identifier": "org/repo",
                    "branch": "main",
                    "service-provider": "github",
                }
            },
        }
    }
    mock_client.get.return_value = ws_data

    vcs = vcs_api.get_workspace_vcs("ws-123")

    assert vcs is not None
    assert vcs.identifier == "org/repo"
    mock_client.get.assert_called_once_with("/workspaces/ws-123")


def test_get_workspace_vcs_not_found(vcs_api, mock_client):
    """Test getting VCS for workspace when it does not have one."""
    ws_data = {"data": {"id": "ws-123", "attributes": {"vcs-repo": None}}}
    mock_client.get.return_value = ws_data

    vcs = vcs_api.get_workspace_vcs("ws-123")

    assert vcs is None


def test_update_workspace_branch(vcs_api, mock_client):
    """Test updating workspace branch."""
    # 1. Mock get_workspace_vcs to return current config
    current_vcs = VCSConnection.model_validate(
        {"identifier": "org/repo", "branch": "old", "service-provider": "github"}
    )
    with patch.object(VCSAPI, "get_workspace_vcs", return_value=current_vcs):
        mock_client.patch.return_value = {
            "data": {
                "id": "ws-123",
                "type": "workspaces",
                "attributes": {"name": "ws1", "vcs-repo": {"branch": "new"}},
            }
        }

        vcs_api.update_workspace_branch("ws-123", "new", "ot-abc")

        # Verify patch payload
        mock_client.patch.assert_called_once()
        args, kwargs = mock_client.patch.call_args
        assert args[0] == "/workspaces/ws-123"
        payload = kwargs["json_data"]
        assert payload["data"]["attributes"]["vcs-repo"]["branch"] == "new"
        assert payload["data"]["attributes"]["vcs-repo"]["oauth-token-id"] == "ot-abc"


def test_list_repositories(vcs_api, mock_client):
    """Test discovering repositories from workspaces."""
    # 1. Mock workspaces list
    ws1 = MagicMock()
    ws1.id = "ws-1"
    ws1.name = "prod"
    ws2 = MagicMock()
    ws2.id = "ws-2"
    ws2.name = "dev"

    with patch("terrapyne.api.workspaces.WorkspaceAPI.list") as mock_ws_list:
        mock_ws_list.return_value = (iter([ws1, ws2]), 2)

        # 2. Mock get_workspace_vcs for each workspace
        vcs1 = VCSConnection.model_validate(
            {
                "identifier": "org/repo",
                "service-provider": "github",
                "repository-http-url": "https://github.com/org/repo",
            }
        )
        vcs2 = VCSConnection.model_validate(
            {
                "identifier": "org/repo",
                "service-provider": "github",
                "repository-http-url": "https://github.com/org/repo",
            }
        )

        # Track calls manually since we're patching the method on the same instance
        with patch.object(VCSAPI, "get_workspace_vcs", side_effect=[vcs1, vcs2]):
            repos = vcs_api.list_repositories("test-org")

            assert len(repos) == 1
            assert repos[0]["identifier"] == "org/repo"
            assert "prod" in repos[0]["workspaces"]
            assert "dev" in repos[0]["workspaces"]


def test_list_connections(vcs_api, mock_client):
    """Test listing VCS connections (stub test)."""
    # Currently it returns empty list, let's verify that
    connections = vcs_api.list_connections("test-org")
    assert connections == []
    mock_client.get.assert_called_once_with("/organizations/test-org/oauth-clients")
