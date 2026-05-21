"""Tests for WorkspaceAPI.list() current-run status filter (org-wide error discovery)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.models.workspace import Workspace


def _make_workspace_response(
    ws_id: str, name: str, run_id: str, run_status: str, created_at: str
) -> dict:
    """Build a minimal TFC API workspace response with an embedded latest run."""
    return {
        "id": ws_id,
        "type": "workspaces",
        "attributes": {
            "name": name,
            "locked": False,
            "tag-names": [],
        },
        "relationships": {
            "latest-run": {"data": {"type": "runs", "id": run_id}},
        },
    }


def _make_run_include(run_id: str, status: str, created_at: str) -> dict:
    return {
        "id": run_id,
        "type": "runs",
        "attributes": {
            "status": status,
            "created-at": created_at,
            "updated-at": created_at,
            "message": None,
            "auto-apply": False,
            "is-destroy": False,
        },
    }


class TestWorkspaceCurrentRunStatusFilter:
    """WorkspaceAPI.list() passes filter[current-run][status] to the TFC API."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_organization.return_value = "Takeda"
        return client

    @pytest.fixture
    def api(self, mock_client):
        return WorkspaceAPI(mock_client)

    def test_list_passes_current_run_status_filter(self, api, mock_client):
        """filter[current-run][status] is forwarded to paginate."""
        mock_client.paginate.return_value = (iter([]), 0)

        list(api.list(current_run_status="errored")[0])

        call_params = mock_client.paginate.call_args[1]["params"]
        assert call_params["filter[current-run][status]"] == "errored"

    def test_list_includes_latest_run_when_filter_set(self, api, mock_client):
        """include=latest-run is added automatically when current_run_status is set."""
        mock_client.paginate.return_value = (iter([]), 0)

        list(api.list(current_run_status="errored")[0])

        call_params = mock_client.paginate.call_args[1]["params"]
        assert "latest-run" in call_params.get("include", "")

    def test_list_no_filter_does_not_add_current_run_param(self, api, mock_client):
        """Without current_run_status, no filter[current-run][status] param is sent."""
        mock_client.paginate.return_value = (iter([]), 0)

        list(api.list()[0])

        call_params = mock_client.paginate.call_args[1]["params"]
        assert "filter[current-run][status]" not in call_params

    def test_list_returns_workspaces_with_latest_run_populated(self, api, mock_client):
        """Workspaces returned by the filter have latest_run populated from included data."""
        ws_data = _make_workspace_response(
            "ws-001", "APMS1234-DEV-eks", "run-aaa", "errored", "2026-04-30T10:00:00Z"
        )
        run_include = _make_run_include("run-aaa", "errored", "2026-04-30T10:00:00Z")

        paginator = MagicMock()
        paginator.__iter__ = MagicMock(return_value=iter([ws_data]))
        paginator.included = [run_include]
        mock_client.paginate.return_value = (paginator, 1)

        workspaces, total = api.list(current_run_status="errored")
        ws_list = list(workspaces)

        assert total == 1
        assert ws_list[0].name == "APMS1234-DEV-eks"
        assert ws_list[0].latest_run is not None
        assert ws_list[0].latest_run.status.value == "errored"

    def test_list_combines_current_run_filter_with_project_filter(self, api, mock_client):
        """Both filter[current-run][status] and filter[project][id] can be set together."""
        mock_client.paginate.return_value = (iter([]), 0)

        list(api.list(current_run_status="errored", project_id="prj-xyz")[0])

        call_params = mock_client.paginate.call_args[1]["params"]
        assert call_params["filter[current-run][status]"] == "errored"
        assert call_params["filter[project][id]"] == "prj-xyz"


class TestOrgWideErroredRunsCommand:
    """tfc run errors without --project uses the org-wide workspace filter."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_organization.return_value = "Takeda"
        return client

    def _errored_workspace(self, name: str, run_id: str, days_ago: int = 1) -> Workspace:
        created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        ws = Workspace.model_construct(
            id=f"ws-{run_id}",
            name=name,
            locked=False,
            tag_names=[],
            latest_run=None,
        )
        from terrapyne.models.run import Run, RunStatus

        ws.latest_run = Run.model_construct(
            id=run_id,
            status=RunStatus.ERRORED,
            created_at=created_at,
            updated_at=created_at,
            message=None,
            auto_apply=False,
            is_destroy=False,
        )
        return ws

    def test_org_wide_scan_calls_workspace_list_with_errored_filter(self, mock_client):
        """run errors (no project) calls workspaces.list(current_run_status='errored')."""
        from terrapyne.api.org_errors import get_errored_workspaces

        mock_client.workspaces.list.return_value = (iter([]), 0)

        list(get_errored_workspaces(mock_client, days=7))

        mock_client.workspaces.list.assert_called_once()
        call_kwargs = mock_client.workspaces.list.call_args[1]
        assert call_kwargs.get("current_run_status") == "errored"

    def test_org_wide_scan_does_not_call_runs_list(self, mock_client):
        """run errors (no project) never calls runs.list per workspace."""
        from terrapyne.api.org_errors import get_errored_workspaces

        mock_client.workspaces.list.return_value = (iter([]), 0)

        list(get_errored_workspaces(mock_client, days=7))

        mock_client.runs.list.assert_not_called()

    def test_org_wide_scan_filters_by_lookback_window(self, mock_client):
        """Workspaces whose latest run errored outside the lookback window are excluded."""
        from terrapyne.api.org_errors import get_errored_workspaces

        recent = self._errored_workspace("ws-recent", "run-001", days_ago=2)
        old = self._errored_workspace("ws-old", "run-002", days_ago=10)

        mock_client.workspaces.list.return_value = (iter([recent, old]), 2)

        results = list(get_errored_workspaces(mock_client, days=7))

        assert len(results) == 1
        assert results[0].name == "ws-recent"

    def test_org_wide_scan_returns_empty_when_no_errors(self, mock_client):
        """Returns empty list when no errored workspaces exist."""
        from terrapyne.api.org_errors import get_errored_workspaces

        mock_client.workspaces.list.return_value = (iter([]), 0)

        results = list(get_errored_workspaces(mock_client, days=7))

        assert results == []

    def test_org_wide_scan_scoped_to_project(self, mock_client):
        """When project_id is given, it is forwarded to workspaces.list."""
        from terrapyne.api.org_errors import get_errored_workspaces

        mock_client.workspaces.list.return_value = (iter([]), 0)
        mock_client.projects.get_by_name.return_value = MagicMock(id="prj-abc")

        list(get_errored_workspaces(mock_client, days=7, project_id="prj-abc"))

        call_kwargs = mock_client.workspaces.list.call_args[1]
        assert call_kwargs.get("project_id") == "prj-abc"
