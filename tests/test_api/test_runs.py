"""Tests for RunsAPI methods, especially run creation and apply operations."""

import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

from terrapyne.api.runs import RunsAPI
from terrapyne.models.plan import Plan
from terrapyne.models.run import Run, RunStatus


class TestRunCreation:
    """Test run creation operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create RunsAPI instance with mock client."""
        return RunsAPI(mock_client)

    @pytest.fixture
    def sample_run_response(self):
        """Sample TFC API response for a run."""
        return {
            "id": "run-abc123",
            "type": "runs",
            "attributes": {
                "status": "pending",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:00:00Z",
                "message": "Plan from Terraform",
                "auto-apply": False,
                "is-destroy": False,
            },
        }

    @pytest.fixture
    def sample_destroy_run_response(self):
        """Sample response for a destroy run."""
        return {
            "id": "run-destroy123",
            "type": "runs",
            "attributes": {
                "status": "pending",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:00:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": True,
            },
        }

    def test_create_run_basic(self, api, mock_client, sample_run_response):
        """Test creating a basic plan run."""
        workspace_id = "ws-abc123"
        mock_client.post.return_value = {"data": sample_run_response}

        run = api.create(workspace_id=workspace_id)

        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/runs"

        # Verify payload structure
        payload = call_args[1]["json_data"]
        assert payload["data"]["type"] == "runs"
        assert payload["data"]["attributes"]["auto-apply"] is False
        assert payload["data"]["attributes"]["is-destroy"] is False
        assert payload["data"]["relationships"]["workspace"]["data"]["id"] == workspace_id

        # Verify returned run
        assert isinstance(run, Run)
        assert run.id == "run-abc123"
        assert run.status == RunStatus.PENDING

    def test_create_run_with_message(self, api, mock_client, sample_run_response):
        """Test creating a run with a message."""
        workspace_id = "ws-abc123"
        message = "Deploy feature-xyz"
        mock_client.post.return_value = {"data": sample_run_response}

        run = api.create(
            workspace_id=workspace_id,
            message=message,
        )

        # Verify message in payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["message"] == message

        # Verify returned run
        assert run.message == "Plan from Terraform"

    def test_create_run_auto_apply(self, api, mock_client):
        """Test creating a run with auto-apply enabled."""
        workspace_id = "ws-abc123"
        response = {
            "id": "run-auto123",
            "type": "runs",
            "attributes": {
                "status": "pending",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:00:00Z",
                "message": None,
                "auto-apply": True,
                "is-destroy": False,
            },
        }
        mock_client.post.return_value = {"data": response}

        run = api.create(
            workspace_id=workspace_id,
            auto_apply=True,
        )

        # Verify auto-apply in payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["auto-apply"] is True

        # Verify returned run
        assert run.auto_apply is True

    def test_create_destroy_run(self, api, mock_client, sample_destroy_run_response):
        """Test creating a destroy run."""
        workspace_id = "ws-abc123"
        mock_client.post.return_value = {"data": sample_destroy_run_response}

        run = api.create(
            workspace_id=workspace_id,
            is_destroy=True,
        )

        # Verify is-destroy in payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["is-destroy"] is True

        # Verify returned run
        assert run.is_destroy is True

    def test_create_run_with_all_options(self, api, mock_client):
        """Test creating a run with all parameters."""
        workspace_id = "ws-abc123"
        response = {
            "id": "run-full123",
            "type": "runs",
            "attributes": {
                "status": "pending",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:00:00Z",
                "message": "Full test run",
                "auto-apply": True,
                "is-destroy": False,
            },
        }
        mock_client.post.return_value = {"data": response}

        run = api.create(
            workspace_id=workspace_id,
            message="Full test run",
            auto_apply=True,
            is_destroy=False,
        )

        # Verify all parameters in payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["message"] == "Full test run"
        assert payload["data"]["attributes"]["auto-apply"] is True
        assert payload["data"]["attributes"]["is-destroy"] is False

        # Verify returned run
        assert run.message == "Full test run"
        assert run.auto_apply is True
        assert run.is_destroy is False


class TestRunApply:
    """Test run apply operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create RunsAPI instance with mock client."""
        return RunsAPI(mock_client)

    @pytest.fixture
    def sample_applied_run_response(self):
        """Sample response for an applied run."""
        return {
            "id": "run-abc123",
            "type": "runs",
            "attributes": {
                "status": "applied",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": "Plan from Terraform",
                "auto-apply": False,
                "is-destroy": False,
            },
        }

    def test_apply_run_basic(self, api, mock_client, sample_applied_run_response):
        """Test applying a run without comment."""
        run_id = "run-abc123"
        mock_client.post.return_value = {"data": sample_applied_run_response}

        run = api.apply(run_id=run_id)

        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/runs/run-abc123/actions/apply"

        # Verify empty payload when no comment
        payload = call_args[1]["json_data"]
        assert payload == {}

        # Verify returned run
        assert isinstance(run, Run)
        assert run.status == RunStatus.APPLIED

    def test_apply_run_with_comment(self, api, mock_client, sample_applied_run_response):
        """Test applying a run with a comment."""
        run_id = "run-abc123"
        comment = "Approved by ops team"
        mock_client.post.return_value = {"data": sample_applied_run_response}

        run = api.apply(
            run_id=run_id,
            comment=comment,
        )

        # Verify comment in payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload == {"comment": comment}

        # Verify returned run
        assert run.status == RunStatus.APPLIED

    def test_apply_run_empty_comment(self, api, mock_client, sample_applied_run_response):
        """Test applying a run with empty comment is treated as no comment."""
        run_id = "run-abc123"
        mock_client.post.return_value = {"data": sample_applied_run_response}

        # Empty string should be falsy and result in empty payload
        run = api.apply(
            run_id=run_id,
            comment="",
        )

        # Verify payload with empty comment is included
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        # Empty string is falsy, so comment should not be included
        assert payload == {}


class TestRunRetrieval:
    """Test run retrieval operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create RunsAPI instance with mock client."""
        return RunsAPI(mock_client)

    def test_get_run(self, api, mock_client):
        """Test retrieving a run by ID."""
        run_id = "run-abc123"
        response = {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": "applied",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": "Production deployment",
                "auto-apply": False,
                "is-destroy": False,
            },
        }
        mock_client.get.return_value = {"data": response}

        run = api.get(run_id)

        # Verify API call
        mock_client.get.assert_called_once_with(f"/runs/{run_id}")

        # Verify returned run
        assert run.id == run_id
        assert run.status == RunStatus.APPLIED

    def test_list_runs(self, api, mock_client):
        """Test listing runs for a workspace."""
        workspace_id = "ws-abc123"
        response_items = [
            {
                "id": "run-1",
                "type": "runs",
                "attributes": {
                    "status": "applied",
                    "created-at": "2024-01-15T10:00:00Z",
                    "updated-at": "2024-01-15T10:05:00Z",
                    "message": None,
                    "auto-apply": False,
                    "is-destroy": False,
                },
            },
            {
                "id": "run-2",
                "type": "runs",
                "attributes": {
                    "status": "planned",
                    "created-at": "2024-01-15T11:00:00Z",
                    "updated-at": "2024-01-15T11:00:00Z",
                    "message": None,
                    "auto-apply": False,
                    "is-destroy": False,
                },
            },
        ]

        mock_client.paginate_with_meta.return_value = (iter(response_items), 2)

        runs, total_count = api.list(workspace_id)

        # Verify returned runs
        assert len(runs) == 2
        assert runs[0].id == "run-1"
        assert runs[1].id == "run-2"
        assert total_count == 2

    def test_list_runs_with_status_filter(self, api, mock_client):
        """Test listing runs filtered by status."""
        workspace_id = "ws-abc123"
        status = "applied"
        response_items = [
            {
                "id": "run-applied",
                "type": "runs",
                "attributes": {
                    "status": "applied",
                    "created-at": "2024-01-15T10:00:00Z",
                    "updated-at": "2024-01-15T10:05:00Z",
                    "message": None,
                    "auto-apply": False,
                    "is-destroy": False,
                },
            },
        ]

        mock_client.paginate_with_meta.return_value = (iter(response_items), 1)

        runs, total_count = api.list(workspace_id, status=status)

        # Verify status filter in call
        call_args = mock_client.paginate_with_meta.call_args
        assert "filter[status]" in call_args[1]["params"]
        assert call_args[1]["params"]["filter[status]"] == status

        # Verify returned runs
        assert len(runs) == 1
        assert runs[0].status == RunStatus.APPLIED


class TestRunPolling:
    """Test run polling operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create RunsAPI instance with mock client."""
        return RunsAPI(mock_client)

    def test_poll_until_complete_immediate_terminal(self, api, mock_client):
        """Test polling when run is already in terminal state."""
        run_id = "run-abc123"
        response = {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": "applied",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
            },
        }
        mock_client.get.return_value = {"data": response}

        run = api.poll_until_complete(run_id)

        # Should only call get once since status is terminal
        mock_client.get.assert_called_once()
        assert run.status == RunStatus.APPLIED

    def test_poll_until_complete_with_transitions(self, api, mock_client):
        """Test polling through state transitions."""
        run_id = "run-abc123"

        # Responses for state transitions
        responses = [
            # First poll: planning
            {
                "id": run_id,
                "type": "runs",
                "attributes": {
                    "status": "planning",
                    "created-at": "2024-01-15T10:00:00Z",
                    "updated-at": "2024-01-15T10:01:00Z",
                    "message": None,
                    "auto-apply": False,
                    "is-destroy": False,
                },
            },
            # Second poll: planned
            {
                "id": run_id,
                "type": "runs",
                "attributes": {
                    "status": "planned",
                    "created-at": "2024-01-15T10:00:00Z",
                    "updated-at": "2024-01-15T10:02:00Z",
                    "message": None,
                    "auto-apply": False,
                    "is-destroy": False,
                },
            },
            # Third poll: applied
            {
                "id": run_id,
                "type": "runs",
                "attributes": {
                    "status": "applied",
                    "created-at": "2024-01-15T10:00:00Z",
                    "updated-at": "2024-01-15T10:05:00Z",
                    "message": None,
                    "auto-apply": False,
                    "is-destroy": False,
                },
            },
        ]

        # Mock get to return responses in sequence
        mock_client.get.side_effect = [{"data": r} for r in responses]

        # Patch sleep to speed up test
        with patch("time.sleep"):
            run = api.poll_until_complete(run_id)

        # Should have called get 3 times (for each state transition)
        assert mock_client.get.call_count == 3
        assert run.status == RunStatus.APPLIED

    def test_poll_with_callback(self, api, mock_client):
        """Test polling with callback function."""
        run_id = "run-abc123"
        callback = MagicMock()

        response = {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": "applied",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
            },
        }
        mock_client.get.return_value = {"data": response}

        run = api.poll_until_complete(run_id, callback=callback)

        # Callback should be called with the run
        callback.assert_called_once()
        assert callback.call_args[0][0].status == RunStatus.APPLIED

    def test_poll_timeout(self, api, mock_client):
        """Test polling timeout."""
        run_id = "run-abc123"

        response = {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": "planning",  # Non-terminal state
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:01:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
            },
        }
        mock_client.get.return_value = {"data": response}

        # Use very short timeout to trigger error quickly
        with pytest.raises(TimeoutError) as exc_info:
            with patch("time.sleep"):
                api.poll_until_complete(run_id, max_wait=0.1)

        assert "did not complete within" in str(exc_info.value)


class TestRunIntegration:
    """Integration tests for run operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create RunsAPI instance with mock client."""
        return RunsAPI(mock_client)

    def test_create_and_apply_workflow(self, api, mock_client):
        """Test complete workflow: create run, wait for plan, apply."""
        workspace_id = "ws-test123"

        # Mock create response
        create_response = {
            "id": "run-workflow123",
            "type": "runs",
            "attributes": {
                "status": "pending",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:00:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
            },
        }
        mock_client.post.return_value = {"data": create_response}

        # Create run
        created_run = api.create(
            workspace_id=workspace_id,
            message="Workflow test",
        )

        assert created_run.id == "run-workflow123"
        assert created_run.status == RunStatus.PENDING

        # Mock get response for planned state
        planned_response = {
            "id": "run-workflow123",
            "type": "runs",
            "attributes": {
                "status": "planned",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:02:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
            },
        }
        mock_client.get.return_value = {"data": planned_response}

        # Get updated run (simulating plan completion)
        planned_run = api.get("run-workflow123")
        assert planned_run.status == RunStatus.PLANNED

        # Mock apply response
        applied_response = {
            "id": "run-workflow123",
            "type": "runs",
            "attributes": {
                "status": "applied",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
            },
        }
        mock_client.post.return_value = {"data": applied_response}

        # Apply run
        applied_run = api.apply("run-workflow123", comment="Approved")
        assert applied_run.status == RunStatus.APPLIED


class TestRunWithPlan:
    """Test run with plan relationship and resource counts."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create RunsAPI instance with mock client."""
        return RunsAPI(mock_client)

    def test_run_extracts_plan_id_from_relationships(self, api, mock_client):
        """Test that Run extracts plan_id from relationships."""
        run_id = "run-with-plan"
        response = {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": "planned",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": "Plan from Terraform",
                "auto-apply": False,
                "is-destroy": False,
                "resource-additions": 0,
                "resource-changes": 0,
                "resource-destructions": 0,
            },
            "relationships": {
                "plan": {
                    "data": {
                        "id": "plan-xyz789",
                        "type": "plans",
                    }
                }
            },
        }
        mock_client.get.return_value = {"data": response}

        run = api.get(run_id)

        # Verify plan_id was extracted
        assert run.plan_id == "plan-xyz789"

    def test_run_without_plan_relationship(self, api, mock_client):
        """Test that Run handles missing plan relationship gracefully."""
        run_id = "run-no-plan"
        response = {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": "pending",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
            },
        }
        mock_client.get.return_value = {"data": response}

        run = api.get(run_id)

        # Verify plan_id is None when no relationship
        assert run.plan_id is None

    def test_run_with_resource_counts(self, api, mock_client):
        """Test that Run can extract resource counts from attributes."""
        run_id = "run-with-counts"
        response = {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": "planned",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
                "resource-additions": 2,
                "resource-changes": 5,
                "resource-destructions": 1,
            },
        }
        mock_client.get.return_value = {"data": response}

        run = api.get(run_id)

        # Verify resource counts from run attributes
        assert run.resource_additions == 2
        assert run.resource_changes == 5
        assert run.resource_destructions == 1

    def test_get_plan_from_run_workflow(self, api, mock_client):
        """Test complete workflow: get run with plan, then fetch plan."""
        run_id = "run-workflow"
        plan_id = "plan-workflow"

        # First call: get run
        run_response = {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": "planned",
                "created-at": "2024-01-15T10:00:00Z",
                "updated-at": "2024-01-15T10:05:00Z",
                "message": None,
                "auto-apply": False,
                "is-destroy": False,
            },
            "relationships": {
                "plan": {
                    "data": {"id": plan_id, "type": "plans"}
                }
            },
        }

        # Second call: get plan
        plan_response = {
            "id": plan_id,
            "type": "plans",
            "attributes": {
                "status": "finished",
                "has-changes": True,
                "resource-additions": 1,
                "resource-changes": 3,
                "resource-destructions": 0,
            },
        }

        mock_client.get.side_effect = [
            {"data": run_response},  # First call for run
            {"data": plan_response},  # Second call for plan
        ]

        # Get run
        run = api.get(run_id)
        assert run.plan_id == plan_id

        # Get plan using plan_id from run
        plan = api.get_plan(plan_id)
        assert plan.resource_changes == 3

        # Verify both calls were made
        assert mock_client.get.call_count == 2
