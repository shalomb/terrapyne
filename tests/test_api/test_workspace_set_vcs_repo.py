"""Tests for WorkspaceAPI.set_vcs_repo (repoint a workspace after a repo rename)."""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.models.workspace import Workspace
from tests.fixtures.factories import workspace_response

OLD_ID = "myorg/old-name"
NEW_ID = "myorg/new-name"


class TestSetVcsRepo:
    """Unit tests for set_vcs_repo API method."""

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
        return workspace_response(
            id="ws-abc123",
            name="my-app-dev",
            vcs_repo={
                "identifier": OLD_ID,
                "branch": "main",
                "repository-http-url": f"https://github.com/{OLD_ID}",
                "oauth-token-id": "ot-abc123",
            },
        )

    @pytest.fixture
    def ws_without_vcs(self):
        resp = workspace_response(id="ws-novcs", name="no-vcs-ws")
        resp["data"]["attributes"]["vcs-repo"] = None
        return resp

    def _repointed(self, ws_with_vcs):
        data = ws_with_vcs["data"]
        data["attributes"]["vcs-repo"]["identifier"] = NEW_ID
        return data

    def test_patches_the_workspace_endpoint(self, api, mock_client, ws_with_vcs):
        """set_vcs_repo must PATCH the workspace-by-name endpoint."""
        mock_client.get.return_value = ws_with_vcs
        mock_client.patch.return_value = {"data": self._repointed(ws_with_vcs)}

        api.set_vcs_repo("my-app-dev", NEW_ID, organization="test-org")

        mock_client.patch.assert_called_once()
        assert mock_client.patch.call_args[0][0] == "/organizations/test-org/workspaces/my-app-dev"

    def test_payload_contains_only_the_identifier(self, api, mock_client, ws_with_vcs):
        """Only vcs-repo.identifier is sent, so the OAuth token and branch are preserved."""
        mock_client.get.return_value = ws_with_vcs
        mock_client.patch.return_value = {"data": self._repointed(ws_with_vcs)}

        api.set_vcs_repo("my-app-dev", NEW_ID, organization="test-org")

        attrs = mock_client.patch.call_args[1]["json_data"]["data"]["attributes"]
        assert list(attrs.keys()) == ["vcs-repo"]
        assert attrs["vcs-repo"] == {"identifier": NEW_ID}

    def test_returns_the_updated_workspace(self, api, mock_client, ws_with_vcs):
        mock_client.get.return_value = ws_with_vcs
        mock_client.patch.return_value = {"data": self._repointed(ws_with_vcs)}

        result = api.set_vcs_repo("my-app-dev", NEW_ID, organization="test-org")

        assert isinstance(result, Workspace)
        assert result.vcs_identifier == NEW_ID

    def test_raises_when_workspace_has_no_vcs(self, api, mock_client, ws_without_vcs):
        mock_client.get.return_value = ws_without_vcs

        with pytest.raises(ValueError, match="no VCS connection"):
            api.set_vcs_repo("no-vcs-ws", NEW_ID, organization="test-org")

        mock_client.patch.assert_not_called()

    @pytest.mark.parametrize("bad", ["", "   ", "no-slash", "a/b/c", "/repo", "owner/", "a b/c"])
    def test_rejects_malformed_identifier_before_any_api_call(self, api, bad):
        """Identifier must be owner/repo; reject anything else without touching the API."""
        with pytest.raises(ValueError, match="identifier must be"):
            api.set_vcs_repo("my-app-dev", bad, organization="test-org")

        api.client.get.assert_not_called()
        api.client.patch.assert_not_called()

    def test_uses_client_org_when_none_given(self, api, mock_client, ws_with_vcs):
        mock_client.get.return_value = ws_with_vcs
        mock_client.patch.return_value = {"data": self._repointed(ws_with_vcs)}

        api.set_vcs_repo("my-app-dev", NEW_ID)

        mock_client.get_organization.assert_any_call(None)
