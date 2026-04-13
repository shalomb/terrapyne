"""Unit tests for RunsAPI critical paths."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from terrapyne.api.runs import RunsAPI
from terrapyne.models.run import Run


class TestRunsAPIList:
    """Test RunsAPI.list() method."""

    @pytest.fixture
    def mock_client(self):
        """Create mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def runs_api(self, mock_client):
        """Create RunsAPI instance."""
        return RunsAPI(mock_client)

    def test_list_with_status_filter(self, runs_api, mock_client):
        """Test listing runs with status filter."""
        mock_run = Mock(spec=Run)
        mock_run.id = "run-123"
        mock_run.status = "planned"

        mock_client.get.return_value = {
            "data": [{"id": "run-123", "type": "runs"}],
            "included": [],
            "meta": {"pagination": {"total-count": 1}},
        }

        with patch.object(Run, "from_api_response", return_value=mock_run):
            runs, total = runs_api.list("ws-123", status="planned")

            assert len(runs) == 1
            assert total == 1
            # Verify status filter was passed
            call_kwargs = mock_client.get.call_args[1]
            assert call_kwargs["params"]["filter[status]"] == "planned"

    def test_list_respects_limit(self, runs_api, mock_client):
        """Test list respects limit parameter."""
        mock_run = Mock(spec=Run)
        mock_client.get.return_value = {
            "data": [{"id": f"run-{i}", "type": "runs"} for i in range(10)],
            "included": [],
            "meta": {"pagination": {"total-count": 10}},
        }

        with patch.object(Run, "from_api_response", return_value=mock_run):
            runs, _ = runs_api.list("ws-123", limit=5)

            assert len(runs) == 5


class TestRunsAPIActive:
    """Test RunsAPI.get_active_runs() method."""

    def test_get_active_runs(self):
        """Test getting active runs."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_run = Mock(spec=Run)
        mock_run.status = "planning"
        mock_client.get.return_value = {
            "data": [{"id": "run-456", "type": "runs"}],
            "included": [],
            "meta": {"pagination": {"total-count": 1}},
        }

        with patch.object(Run, "from_api_response", return_value=mock_run):
            active = runs_api.get_active_runs("ws-123")

            assert len(active) == 1
            # Verify status filter includes active statuses
            call_kwargs = mock_client.get.call_args[1]
            assert "filter[status]" in call_kwargs["params"]
            assert "planning" in call_kwargs["params"]["filter[status]"]


class TestRunsAPICostEstimate:
    """Test RunsAPI.get_latest_cost_estimate() method."""

    def test_get_latest_cost_estimate_found(self):
        """Test retrieving latest cost estimate when available."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_client.get.return_value = {
            "data": [
                {"id": "run-789", "relationships": {"cost-estimate": {"data": {"id": "ce-1"}}}}
            ],
            "included": [
                {
                    "id": "ce-1",
                    "type": "cost-estimates",
                    "attributes": {"status": "finished", "proposed-monthly-cost": "100.00"},
                }
            ],
        }

        result = runs_api.get_latest_cost_estimate("ws-123")

        assert result is not None
        assert result["proposed-monthly-cost"] == "100.00"

    def test_get_latest_cost_estimate_not_finished(self):
        """Test cost estimate returns None if not finished."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_client.get.return_value = {
            "data": [
                {"id": "run-789", "relationships": {"cost-estimate": {"data": {"id": "ce-1"}}}}
            ],
            "included": [
                {"id": "ce-1", "type": "cost-estimates", "attributes": {"status": "pending"}}
            ],
        }

        result = runs_api.get_latest_cost_estimate("ws-123")

        assert result is None

    def test_get_latest_cost_estimate_no_runs(self):
        """Test cost estimate returns None when no runs."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_client.get.return_value = {"data": [], "included": []}

        result = runs_api.get_latest_cost_estimate("ws-123")

        assert result is None


class TestRunsAPICreate:
    """Test RunsAPI.create() method."""

    def test_create_basic_run(self):
        """Test creating a basic run."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_run = Mock(spec=Run)
        mock_run.id = "run-new"
        mock_client.post.return_value = {"data": {"id": "run-new", "type": "runs"}}

        with patch.object(Run, "from_api_response", return_value=mock_run):
            run = runs_api.create("ws-123")

            assert run.id == "run-new"

    def test_create_with_auto_apply(self):
        """Test creating run with auto-apply."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_client.post.return_value = {"data": {"id": "run-new", "type": "runs"}}

        with patch.object(Run, "from_api_response"):
            runs_api.create("ws-123", auto_apply=True)

            # Verify auto-apply was set in payload
            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["json_data"]["data"]["attributes"]["auto-apply"] is True

    def test_create_destroy_run(self):
        """Test creating destroy run."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_client.post.return_value = {"data": {"id": "run-destroy", "type": "runs"}}

        with patch.object(Run, "from_api_response"):
            runs_api.create("ws-123", is_destroy=True, message="Destroy all")

            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["json_data"]["data"]["attributes"]["is-destroy"] is True
            assert call_kwargs["json_data"]["data"]["attributes"]["message"] == "Destroy all"


class TestRunsAPIActions:
    """Test RunsAPI action methods (apply, discard, cancel)."""

    def test_apply_run(self):
        """Test applying a run."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_run = Mock(spec=Run)
        mock_client.post.return_value = None
        mock_client.get.return_value = {"data": {"id": "run-123", "status": "applied"}}

        with patch.object(runs_api, "get", return_value=mock_run):
            result = runs_api.apply("run-123", comment="Approved")

            assert result == mock_run
            # Verify comment was sent
            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["json_data"]["comment"] == "Approved"

    def test_discard_run(self):
        """Test discarding a run."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_run = Mock(spec=Run)
        mock_client.post.return_value = None

        with patch.object(runs_api, "get", return_value=mock_run):
            result = runs_api.discard("run-123")

            assert result == mock_run

    def test_cancel_run(self):
        """Test canceling a run."""
        mock_client = MagicMock()
        runs_api = RunsAPI(mock_client)

        mock_run = Mock(spec=Run)
        mock_client.post.return_value = None

        with patch.object(runs_api, "get", return_value=mock_run):
            result = runs_api.cancel("run-123")

            assert result == mock_run
