"""Tests for the RunTrigger model."""

from terrapyne.models.run_trigger import RunTrigger


class TestRunTriggerModel:
    """Unit tests for RunTrigger."""

    def _api_response(
        self,
        id="rt-abc123",
        source_workspace_id="ws-upstream1",
        source_workspace_name="upstream-workspace",
        created_at="2026-01-15T10:00:00.000Z",
    ):
        return {
            "id": id,
            "type": "run-triggers",
            "attributes": {
                "created-at": created_at,
            },
            "relationships": {
                "source-workspace": {"data": {"id": source_workspace_id, "type": "workspaces"}}
            },
            "included": [
                {
                    "id": source_workspace_id,
                    "type": "workspaces",
                    "attributes": {"name": source_workspace_name},
                }
            ],
        }

    def test_from_api_response_sets_id(self):
        data = self._api_response()
        trigger = RunTrigger.from_api_response(data, included=data["included"])
        assert trigger.id == "rt-abc123"

    def test_from_api_response_sets_source_workspace_id(self):
        data = self._api_response()
        trigger = RunTrigger.from_api_response(data, included=data["included"])
        assert trigger.source_workspace_id == "ws-upstream1"

    def test_from_api_response_sets_source_workspace_name_from_included(self):
        data = self._api_response()
        trigger = RunTrigger.from_api_response(data, included=data["included"])
        assert trigger.source_workspace_name == "upstream-workspace"

    def test_from_api_response_source_workspace_name_none_when_no_included(self):
        data = self._api_response()
        trigger = RunTrigger.from_api_response(data, included=[])
        assert trigger.source_workspace_name is None

    def test_from_api_response_sets_created_at(self):
        data = self._api_response()
        trigger = RunTrigger.from_api_response(data, included=data["included"])
        assert trigger.created_at is not None
