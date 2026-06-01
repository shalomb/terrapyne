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
        mock_client.get.assert_called_with("/runs/run-abc123", params={"include": "plan"})

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

    def test_get_run_always_includes_plan_sideload(self, api, mock_client):
        """runs.get() must always request include=plan so plan_status is populated.

        B5: Without this, plan_status is always None and get_error_summary
        cannot determine whether the error is in the plan or apply stage.
        """
        plan_id = "plan-xyz"
        run_id = "run-abc123"
        mock_client.get.return_value = {
            "data": {
                "id": run_id,
                "type": "runs",
                "attributes": {
                    "status": "errored",
                    "created-at": "2024-01-15T10:00:00Z",
                    "updated-at": "2024-01-15T10:05:00Z",
                    "message": "Deploy failed",
                    "auto-apply": True,
                    "is-destroy": False,
                },
                "relationships": {
                    "plan": {"data": {"id": plan_id, "type": "plans"}},
                },
            },
            "included": [
                {
                    "id": plan_id,
                    "type": "plans",
                    "attributes": {
                        "status": "finished",
                        "has-changes": True,
                        "resource-additions": 0,
                        "resource-changes": 0,
                        "resource-destructions": 0,
                        "resource-imports": 0,
                        "action-invocations": 0,
                    },
                }
            ],
        }

        run = api.get(run_id)

        # plan sideload was requested
        call_params = mock_client.get.call_args[1]["params"]
        assert "include" in call_params
        assert "plan" in call_params["include"]

        # plan_status is populated from the sideload
        assert run.plan_status == "finished"

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

        # include=plan is always present (B5 fix)
        call_params = mock_client.get.call_args[1]["params"]
        assert "plan" in call_params.get("include", "")

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


class TestRunStatusActiveStatuses:
    """Tests for RunStatus.get_active_statuses() return type."""

    def test_get_active_statuses_returns_list_of_run_status(self):
        """get_active_statuses() must return list[RunStatus], not list[str]."""
        statuses = RunStatus.get_active_statuses()
        assert len(statuses) > 0
        assert all(isinstance(s, RunStatus) for s in statuses)

    def test_get_active_statuses_excludes_terminal_states(self):
        """Terminal states must not appear in active statuses."""
        statuses = RunStatus.get_active_statuses()
        terminal = {
            RunStatus.APPLIED,
            RunStatus.ERRORED,
            RunStatus.CANCELED,
            RunStatus.FORCE_CANCELED,
            RunStatus.DISCARDED,
        }
        assert not terminal.intersection(statuses)


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


class TestPollUntilComplete:
    """Tests for poll_until_complete with on_stall callback."""

    def _make_run(self, run_id: str, status: RunStatus, workspace_id: str = "ws-123") -> Run:
        return Run.model_construct(id=run_id, status=status, workspace_id=workspace_id)

    def _make_api(self, get_side_effect):
        mock_client = MagicMock()
        api = RunsAPI(mock_client)
        api.get = MagicMock(side_effect=get_side_effect)
        return api

    def test_on_stall_fires_once_when_pending_exceeds_threshold(self):
        """on_stall callback fires once after pending exceeds pending_hint_after."""
        pending_run = self._make_run("run-1", RunStatus.PENDING)
        applied_run = self._make_run("run-1", RunStatus.APPLIED)

        # Needs: pending (t=0), pending (t=61, stall fires), applied (terminal)
        calls = iter([pending_run, pending_run, applied_run])
        api = self._make_api(lambda _: next(calls))

        stall_calls = []

        with pytest.MonkeyPatch().context() as mp:
            # time.time() calls in order:
            # 1: start_time=0.0
            # 2: loop1 now=1.0  → pending_since=1.0
            # 3: loop2 now=65.0 → pending_elapsed=64.0 >= 60 → fires stall
            # 4: loop3 now=65.1 → applied, terminal
            times = iter([0.0, 1.0, 65.0, 65.1])
            mp.setattr("time.sleep", lambda s: None)
            mp.setattr("time.time", lambda: next(times))

            api.poll_until_complete(
                "run-1",
                pending_hint_after=60.0,
                on_stall=lambda run, elapsed: stall_calls.append((run, elapsed)),
            )

        assert len(stall_calls) == 1
        assert stall_calls[0][0] is pending_run
        assert stall_calls[0][1] >= 60.0

    def test_on_stall_does_not_fire_when_not_pending(self):
        """on_stall is not called when run is in a non-pending active state."""
        planning_run = self._make_run("run-1", RunStatus.PLANNING)
        applied_run = self._make_run("run-1", RunStatus.APPLIED)

        calls = iter([planning_run, applied_run])
        api = self._make_api(lambda _: next(calls))

        stall_calls = []

        with pytest.MonkeyPatch().context() as mp:
            # start_time=0, loop1(planning) now=1.0; loop2(applied) is terminal, no now call
            times = iter([0.0, 1.0])
            mp.setattr("time.sleep", lambda s: None)
            mp.setattr("time.time", lambda: next(times))

            api.poll_until_complete(
                "run-1",
                pending_hint_after=60.0,
                on_stall=lambda run, elapsed: stall_calls.append((run, elapsed)),
            )

        assert len(stall_calls) == 0

    def test_on_stall_fires_only_once_across_multiple_pending_polls(self):
        """on_stall fires exactly once even if run stays pending through many polls."""
        pending = self._make_run("run-1", RunStatus.PENDING)
        applied = self._make_run("run-1", RunStatus.APPLIED)

        # 3 pending polls then applied
        calls = iter([pending, pending, pending, applied])
        api = self._make_api(lambda _: next(calls))

        stall_calls = []

        with pytest.MonkeyPatch().context() as mp:
            # start=0; loop1(pending) now=1.0 → pending_since=1; loop2(pending) now=65 → fires
            # loop3(pending) now=66 → already fired; loop4(applied) terminal, no now call
            times = iter([0.0, 1.0, 65.0, 66.0])
            mp.setattr("time.sleep", lambda s: None)
            mp.setattr("time.time", lambda: next(times))

            api.poll_until_complete(
                "run-1",
                pending_hint_after=60.0,
                on_stall=lambda run, elapsed: stall_calls.append((run, elapsed)),
            )

        assert len(stall_calls) == 1

    def test_on_stall_resets_when_status_leaves_pending(self):
        """Pending timer resets when status changes out of pending; re-fires after new stall."""
        pending1 = self._make_run("run-1", RunStatus.PENDING)
        planning = self._make_run("run-1", RunStatus.PLANNING)
        pending2 = self._make_run("run-1", RunStatus.PENDING)
        applied = self._make_run("run-1", RunStatus.APPLIED)

        # pending1, planning, pending2, pending2 (stall fires), applied
        calls = iter([pending1, planning, pending2, pending2, applied])
        api = self._make_api(lambda _: next(calls))

        stall_calls = []

        with pytest.MonkeyPatch().context() as mp:
            # start=0; loop1(p1) now=1 → pending_since=1; loop2(planning) now=2 → reset
            # loop3(p2) now=3 → pending_since=3; loop4(p2) now=70 → elapsed=67 → fires
            # loop5(applied) terminal, no now call
            times = iter([0.0, 1.0, 2.0, 3.0, 70.0])
            mp.setattr("time.sleep", lambda s: None)
            mp.setattr("time.time", lambda: next(times))

            api.poll_until_complete(
                "run-1",
                pending_hint_after=60.0,
                on_stall=lambda run, elapsed: stall_calls.append((run, elapsed)),
            )

        assert len(stall_calls) == 1

    def test_poll_without_on_stall_still_works(self):
        """poll_until_complete works normally when on_stall is not provided."""
        applied = self._make_run("run-1", RunStatus.APPLIED)
        calls = iter([applied])
        api = self._make_api(lambda _: next(calls))

        with pytest.MonkeyPatch().context() as mp:
            times = iter([0.0])
            mp.setattr("time.sleep", lambda s: None)
            mp.setattr("time.time", lambda: next(times))

            result = api.poll_until_complete("run-1")

        assert result.status == RunStatus.APPLIED
