"""Regression tests for B9: workspace name lookup via direct endpoint.

Ensures workspaces.get() resolves names using the direct
/organizations/{org}/workspaces/{name} endpoint rather than fuzzy
search[name], which returns partial matches.
"""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.models.workspace import Workspace
from tests.fixtures.factories import workspace_response


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.get_organization.return_value = "test-org"
    return client


@pytest.fixture
def api(mock_client):
    return WorkspaceAPI(mock_client)


def _ws_data(name="my-app-dev", id="ws-abc123"):
    resp = workspace_response(id=id, name=name)
    return {**resp, "included": []}


class TestWorkspaceGetDirectEndpoint:
    """workspaces.get() must use the direct endpoint, not fuzzy search."""

    def test_get_uses_direct_path(self, api, mock_client):
        """get() hits /organizations/{org}/workspaces/{name} directly."""
        mock_client.get.return_value = _ws_data("my-app-dev")

        api.get("my-app-dev", organization="test-org")

        mock_client.get.assert_called_once()
        path = mock_client.get.call_args[0][0]
        assert path == "/organizations/test-org/workspaces/my-app-dev"

    def test_get_does_not_use_search_param(self, api, mock_client):
        """get() must NOT pass search[name] as a query parameter."""
        mock_client.get.return_value = _ws_data("my-app-dev")

        api.get("my-app-dev", organization="test-org")

        params = mock_client.get.call_args[1].get("params", {})
        assert "search[name]" not in params
        assert "filter[names]" not in params

    def test_get_hyphenated_name_with_digits(self, api, mock_client):
        """B9 regression: workspace names with hyphens and digits are resolved correctly."""
        ws_name = "tec-dce-inn-dev-93400-shalombhooshi"
        mock_client.get.return_value = _ws_data(ws_name, id="ws-tecdce123")

        result = api.get(ws_name, organization="test-org")

        assert isinstance(result, Workspace)
        assert result.name == ws_name

        path = mock_client.get.call_args[0][0]
        assert ws_name in path
        assert path == f"/organizations/test-org/workspaces/{ws_name}"

    def test_get_returns_workspace_model(self, api, mock_client):
        """get() returns a Workspace instance."""
        mock_client.get.return_value = _ws_data("my-app-dev")

        result = api.get("my-app-dev", organization="test-org")

        assert isinstance(result, Workspace)
        assert result.name == "my-app-dev"

    @pytest.mark.parametrize(
        "ws_name",
        [
            "simple",
            "with-hyphens",
            "with-digits-123",
            "tec-dce-inn-dev-93400-shalombhooshi",
            "multi-segment-99-name-with-many-parts",
        ],
    )
    def test_get_various_name_formats(self, api, mock_client, ws_name):
        """Direct endpoint works for all workspace name formats."""
        mock_client.get.return_value = _ws_data(ws_name, id=f"ws-{ws_name[:8]}")

        api.get(ws_name, organization="test-org")

        path = mock_client.get.call_args[0][0]
        assert path == f"/organizations/test-org/workspaces/{ws_name}"
