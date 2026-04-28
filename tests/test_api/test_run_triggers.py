"""Tests for RunTriggersAPI."""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.run_triggers import RunTriggersAPI
from terrapyne.models.run_trigger import RunTrigger


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def api(mock_client):
    return RunTriggersAPI(mock_client)


def _trigger_response(
    id="rt-abc123",
    source_ws_id="ws-upstream1",
    source_ws_name="upstream-ws",
):
    return {
        "id": id,
        "type": "run-triggers",
        "attributes": {"created-at": "2026-01-15T10:00:00.000Z"},
        "relationships": {"source-workspace": {"data": {"id": source_ws_id, "type": "workspaces"}}},
    }


def _included_workspace(id="ws-upstream1", name="upstream-ws"):
    return {"id": id, "type": "workspaces", "attributes": {"name": name}}


class TestRunTriggersAPIList:
    def test_list_calls_get_with_correct_path(self, api, mock_client):
        mock_client.get.return_value = {"data": [], "included": []}
        api.list("ws-downstream1")
        mock_client.get.assert_called_once()
        call_path = mock_client.get.call_args[0][0]
        assert call_path == "/workspaces/ws-downstream1/run-triggers"

    def test_list_passes_include_param(self, api, mock_client):
        mock_client.get.return_value = {"data": [], "included": []}
        api.list("ws-downstream1")
        params = (
            mock_client.get.call_args[1].get("params", {}) or mock_client.get.call_args[0][1]
            if len(mock_client.get.call_args[0]) > 1
            else mock_client.get.call_args[1].get("params", {})
        )
        assert "filter[run-trigger][type]" in params or "include" in params

    def test_list_returns_run_trigger_objects(self, api, mock_client):
        mock_client.get.return_value = {
            "data": [_trigger_response()],
            "included": [_included_workspace()],
        }
        triggers = api.list("ws-downstream1")
        assert len(triggers) == 1
        assert isinstance(triggers[0], RunTrigger)

    def test_list_resolves_source_workspace_name(self, api, mock_client):
        mock_client.get.return_value = {
            "data": [_trigger_response(source_ws_id="ws-up1", source_ws_name="up-ws")],
            "included": [_included_workspace(id="ws-up1", name="up-ws")],
        }
        triggers = api.list("ws-downstream1")
        assert triggers[0].source_workspace_name == "up-ws"

    def test_list_returns_empty_for_no_triggers(self, api, mock_client):
        mock_client.get.return_value = {"data": [], "included": []}
        assert api.list("ws-downstream1") == []


class TestRunTriggersAPIAdd:
    def test_add_calls_post_with_correct_path(self, api, mock_client):
        mock_client.post.return_value = {
            "data": _trigger_response(),
            "included": [_included_workspace()],
        }
        api.add(workspace_id="ws-downstream1", source_workspace_id="ws-upstream1")
        mock_client.post.assert_called_once()
        call_path = mock_client.post.call_args[0][0]
        assert call_path == "/workspaces/ws-downstream1/run-triggers"

    def test_add_sends_correct_payload(self, api, mock_client):
        mock_client.post.return_value = {
            "data": _trigger_response(),
            "included": [_included_workspace()],
        }
        api.add(workspace_id="ws-downstream1", source_workspace_id="ws-upstream1")
        json_data = (
            mock_client.post.call_args[1].get("json_data") or mock_client.post.call_args[0][1]
        )
        assert json_data["data"]["type"] == "run-triggers"
        assert json_data["data"]["relationships"]["sourceable"]["data"]["id"] == "ws-upstream1"
        assert json_data["data"]["relationships"]["sourceable"]["data"]["type"] == "workspaces"

    def test_add_returns_run_trigger(self, api, mock_client):
        mock_client.post.return_value = {
            "data": _trigger_response(),
            "included": [_included_workspace()],
        }
        trigger = api.add(workspace_id="ws-downstream1", source_workspace_id="ws-upstream1")
        assert isinstance(trigger, RunTrigger)
        assert trigger.id == "rt-abc123"


class TestRunTriggersAPIRemove:
    def test_remove_calls_delete_with_correct_path(self, api, mock_client):
        api.remove(run_trigger_id="rt-abc123")
        mock_client.delete.assert_called_once_with("/run-triggers/rt-abc123")

    def test_remove_returns_none(self, api, mock_client):
        mock_client.delete.return_value = None
        result = api.remove(run_trigger_id="rt-abc123")
        assert result is None
