"""Unit tests for State Versions API."""
import json
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

import pytest
from terrapyne.api.state_versions import StateVersionsAPI
from terrapyne.models.state_version import StateVersion, StateVersionOutput


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.get_organization.return_value = "test-org"
    return client


@pytest.fixture
def api(mock_client):
    return StateVersionsAPI(mock_client)


def test_list_state_versions(api, mock_client):
    """Test listing state versions for a workspace."""
    mock_client.paginate_with_meta.return_value = (
        [
            {
                "id": "sv-1",
                "attributes": {"serial": 1, "status": "complete", "resource-count": 10},
            },
            {
                "id": "sv-2",
                "attributes": {"serial": 2, "status": "complete", "resource-count": 15},
            },
        ],
        2,
    )

    versions, total = api.list(organization="test-org", workspace_name="test-ws")

    assert len(versions) == 2
    assert versions[0].id == "sv-1"
    assert versions[1].id == "sv-2"
    assert total == 2
    mock_client.paginate_with_meta.assert_called_once()


def test_get_state_version(api, mock_client):
    """Test getting a single state version by ID."""
    mock_client.get.return_value = {
        "data": {
            "id": "sv-abc",
            "attributes": {"serial": 5, "status": "complete"},
        }
    }

    sv = api.get("sv-abc")

    assert sv.id == "sv-abc"
    assert sv.serial == 5
    mock_client.get.assert_called_with("/state-versions/sv-abc")


def test_get_current_state_version(api, mock_client):
    """Test getting the current state version for a workspace."""
    mock_client.get.return_value = {
        "data": {
            "id": "sv-latest",
            "attributes": {"serial": 10, "status": "complete"},
        }
    }

    sv = api.get_current("ws-123")

    assert sv.id == "sv-latest"
    mock_client.get.assert_called_with("/workspaces/ws-123/current-state-version")


def test_list_outputs(api, mock_client):
    """Test listing outputs for a state version."""
    mock_client.paginate.return_value = [
        {
            "attributes": {
                "name": "db_url",
                "value": "postgres://host",
                "type": "string",
                "sensitive": False,
            }
        },
        {
            "attributes": {
                "name": "db_pass",
                "value": None,
                "type": "string",
                "sensitive": True,
            }
        },
    ]

    outputs = api.list_outputs("sv-abc")

    assert len(outputs) == 2
    assert outputs[0].name == "db_url"
    assert outputs[0].value == "postgres://host"
    assert outputs[1].name == "db_pass"
    assert outputs[1].sensitive is True


def test_find_version_before(api, mock_client):
    """Test finding a state version before a given date."""
    before_dt = datetime(2023, 1, 1, tzinfo=UTC)

    mock_client.paginate.return_value = [
        {
            "id": "sv-new",
            "attributes": {"created-at": "2023-01-02T00:00:00Z", "serial": 10},
        },
        {
            "id": "sv-target",
            "attributes": {"created-at": "2022-12-31T23:59:59Z", "serial": 9},
        },
        {
            "id": "sv-old",
            "attributes": {"created-at": "2022-12-30T00:00:00Z", "serial": 8},
        },
    ]

    # Need to mock WorkspaceAPI for name resolution
    with patch("terrapyne.api.workspaces.WorkspaceAPI") as ws_api_mock:
        ws_mock = MagicMock()
        ws_mock.name = "test-ws"
        ws_api_mock.return_value.get_by_id.return_value = ws_mock

        sv = api.find_version_before("ws-abc", before_dt)

    assert sv is not None
    assert sv.id == "sv-target"
    assert sv.serial == 9
