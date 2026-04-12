"""Tests for RunsAPI methods, especially run creation and apply operations."""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.runs import RunsAPI
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
        # In our implementation we don't send 'type' in attributes, it's just 'data'
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
        mock_client.get.return_value = {"data": sample_applied_run_response}

        run = api.apply(run_id=run_id)

        # Verify API calls
        mock_client.post.assert_called_once_with("/runs/run-abc123/actions/apply", json_data=None)
        mock_client.get.assert_called_with("/runs/run-abc123", params={})

        # Verify returned run
        assert isinstance(run, Run)
        assert run.status == RunStatus.APPLIED

    def test_apply_run_with_comment(self, api, mock_client, sample_applied_run_response):
        """Test applying a run with a comment."""
        run_id = "run-abc123"
        comment = "Approved by ops team"
        mock_client.get.return_value = {"data": sample_applied_run_response}

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
        mock_client.get.return_value = {"data": sample_applied_run_response}

        api.apply(
            run_id=run_id,
            comment="",
        )

        # Verify payload with empty comment is NOT included (empty string is falsy)
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload is None


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
        mock_client.get.assert_called_once_with(f"/runs/{run_id}", params={})

        # Verify returned run
        assert run.id == run_id
        assert run.status == RunStatus.APPLIED

    def test_list_runs(self, api, mock_client):
        """Test listing runs for a workspace."""
        workspace_id = "ws-abc123"
        response = {
            "data": [
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
            ],
            "meta": {"pagination": {"total-count": 2}},
        }

        mock_client.get.return_value = response

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
        response = {
            "data": [
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
                }
            ],
            "meta": {"pagination": {"total-count": 1}},
        }

        mock_client.get.return_value = response

        runs, _total_count = api.list(workspace_id, status=status)

        # Verify status filter in params
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["filter[status]"] == status

        assert len(runs) == 1
        assert runs[0].status == RunStatus.APPLIED


class TestRunIntegration:
    """Test full run lifecycle workflows."""

    def test_create_and_apply_workflow(self):
        """Test the sequence of triggering and then applying a run."""
        mock_client = MagicMock()
        api = RunsAPI(mock_client)
        workspace_id = "ws-abc123"
        run_id = "run-123"

        # 1. Trigger run
        mock_client.post.return_value = {
            "data": {
                "id": run_id,
                "type": "runs",
                "attributes": {"status": "planned", "auto-apply": False},
            }
        }
        run = api.create(workspace_id=workspace_id)
        assert run.status == RunStatus.PLANNED

        # 2. Apply run
        mock_client.get.return_value = {
            "data": {
                "id": run_id,
                "type": "runs",
                "attributes": {"status": "applied", "auto-apply": False},
            }
        }
        updated_run = api.apply(run_id=run_id)
        assert updated_run.status == RunStatus.APPLIED
