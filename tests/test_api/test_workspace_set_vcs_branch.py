"""Tests for WorkspaceAPI.set_vcs_branch (F13)."""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.models.workspace import Workspace
from tests.fixtures.factories import workspace_response


class TestSetVcsBranch:
    """Unit tests for set_vcs_branch API method."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_organization.return_value = "test-org"
        return client

    @pytest.fixture
    def api(self, mock_client):
        return WorkspaceAPI(mock_client)

    @pytest.fixture
    def ws_with_vcs(self):
        """Workspace response with VCS connected."""
        return workspace_response(
            id="ws-abc123",
            name="my-app-dev",
            vcs_repo={
                "identifier": "myorg/my-app",
                "branch": "main",
                "repository-http-url": "https://github.com/myorg/my-app",
                "oauth-token-id": "ot-abc123",
            },
        )

    @pytest.fixture
    def ws_without_vcs(self):
        """Workspace response with no VCS connected."""
        resp = workspace_response(id="ws-novcs", name="no-vcs-ws")
        # Explicitly clear vcs-repo so the workspace has no VCS
        resp["data"]["attributes"]["vcs-repo"] = None
        return resp

    def test_set_vcs_branch_sends_patch_request(self, api, mock_client, ws_with_vcs):
        """set_vcs_branch must PATCH the workspace endpoint."""
        ws_data = ws_with_vcs["data"]
        ws_data["attributes"]["vcs-repo"]["branch"] = "feature/my-change"
        mock_client.get.return_value = ws_with_vcs
        mock_client.patch.return_value = {"data": ws_data}

        api.set_vcs_branch("my-app-dev", "feature/my-change", organization="test-org")

        mock_client.patch.assert_called_once()
        path = mock_client.patch.call_args[0][0]
        assert path == "/organizations/test-org/workspaces/my-app-dev"

    def test_set_vcs_branch_payload_structure(self, api, mock_client, ws_with_vcs):
        """Payload must contain vcs-repo.branch only."""
        ws_data = ws_with_vcs["data"]
        ws_data["attributes"]["vcs-repo"]["branch"] = "feature/my-change"
        mock_client.get.return_value = ws_with_vcs
        mock_client.patch.return_value = {"data": ws_data}

        api.set_vcs_branch("my-app-dev", "feature/my-change", organization="test-org")

        payload = mock_client.patch.call_args[1]["json_data"]
        assert payload["data"]["type"] == "workspaces"
        assert payload["data"]["attributes"]["vcs-repo"]["branch"] == "feature/my-change"
        # Must NOT include other attributes (lean patch)
        assert "name" not in payload["data"]["attributes"]
        assert "terraform-version" not in payload["data"]["attributes"]
        # vcs-repo object must contain ONLY branch — no identifier/oauth-token-id leakage
        assert list(payload["data"]["attributes"]["vcs-repo"].keys()) == ["branch"]

    def test_set_vcs_branch_returns_workspace(self, api, mock_client, ws_with_vcs):
        """set_vcs_branch must return a Workspace instance."""
        ws_data = ws_with_vcs["data"]
        ws_data["attributes"]["vcs-repo"]["branch"] = "feature/my-change"
        mock_client.get.return_value = ws_with_vcs
        mock_client.patch.return_value = {"data": ws_data}

        result = api.set_vcs_branch("my-app-dev", "feature/my-change", organization="test-org")

        assert isinstance(result, Workspace)
        assert result.vcs_branch == "feature/my-change"

    def test_set_vcs_branch_raises_when_no_vcs(self, api, mock_client, ws_without_vcs):
        """set_vcs_branch must raise ValueError when workspace has no VCS."""
        mock_client.get.return_value = ws_without_vcs

        with pytest.raises(ValueError, match="no VCS connection"):
            api.set_vcs_branch("no-vcs-ws", "feature/new", organization="test-org")

        mock_client.patch.assert_not_called()

    def test_set_vcs_branch_uses_client_org_when_none_given(self, api, mock_client, ws_with_vcs):
        """When organization=None, get_organization is called with None first."""
        ws_data = ws_with_vcs["data"]
        mock_client.get.return_value = ws_with_vcs
        mock_client.patch.return_value = {"data": ws_data}

        api.set_vcs_branch("my-app-dev", "hotfix/123")

        # get_organization(None) must be in the call list (first call from set_vcs_branch)
        mock_client.get_organization.assert_any_call(None)
