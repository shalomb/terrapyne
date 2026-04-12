"""Unit tests for log streaming pure functions and generator."""

import pytest
import time
from unittest.mock import MagicMock, patch
from terrapyne.cli.run_cmd import _extract_new_lines, _fetch_run_logs_incrementally
from terrapyne.models.run import Run, RunStatus


class TestExtractNewLines:
    """Test offset-tracking logic for incremental log extraction."""

    def test_first_fetch_returns_all_content(self):
        """When previous is empty, all current content should be returned."""
        previous = ""
        current = "Terraform v1.7.0\nPlan: 2 to add"

        result = _extract_new_lines(previous, current)

        assert result == ["Terraform v1.7.0", "Plan: 2 to add"]

    def test_second_fetch_returns_only_delta(self):
        """When previous has content, only new lines should be returned."""
        previous = "Terraform v1.7.0\n"
        current = "Terraform v1.7.0\nPlan: 2 to add\nDone."

        result = _extract_new_lines(previous, current)

        # Only the new content after the previous buffer length
        assert result == ["Plan: 2 to add", "Done."]

    def test_identical_content_returns_empty(self):
        """When content hasn't changed, return empty list."""
        previous = "Terraform v1.7.0\nPlan: 2 to add\n"
        current = "Terraform v1.7.0\nPlan: 2 to add\n"

        result = _extract_new_lines(previous, current)

        assert result == []

    def test_shorter_content_returns_empty(self):
        """When current is shorter than previous, return empty (regression guard)."""
        previous = "Terraform v1.7.0\nPlan: 2 to add\nDone."
        current = "Terraform v1.7.0\n"

        result = _extract_new_lines(previous, current)

        assert result == []


class TestStreamRunLogs:
    """Test log streaming generator behavior."""

    def _make_run(self, run_id, status, plan_id=None, apply_id=None):
        """Helper to construct a Run instance without full API validation."""
        return Run.model_construct(
            id=run_id,
            status=RunStatus(status),
            plan_id=plan_id,
            apply_id=apply_id,
        )

    def test_yields_plan_lines_incrementally(self):
        """Generator should yield plan log lines as they arrive across cycles."""
        run_id = "run-123"
        plan_id = "plan-456"

        # Simulate log growth from cycle 1 to cycle 2, then terminal on cycle 3
        plan_logs = [
            "Terraform v1.7.0",  # Cycle 1 fetch
            "Terraform v1.7.0\nPlan: 2 to add",  # Cycle 2 fetch
            "Terraform v1.7.0\nPlan: 2 to add",  # Cycle 3 fetch (before terminal check)
        ]

        # Create runs: planning for cycles 1&2, then planned (terminal) for cycle 3
        planning_run = self._make_run(run_id, "planning", plan_id=plan_id)
        planned_run = self._make_run(run_id, "planned", plan_id=plan_id)

        # Use a function to manage cycle count
        get_call_count = [0]
        def get_side_effect(run_id):
            get_call_count[0] += 1
            if get_call_count[0] <= 2:
                return planning_run
            else:
                return planned_run

        mock_client = MagicMock()
        mock_client.runs.get.side_effect = get_side_effect
        mock_client.runs.get_plan_logs.side_effect = plan_logs
        mock_sleep = MagicMock()

        # Patch monotonic to prevent max_wait timeout
        with patch("terrapyne.cli.run_cmd.time.monotonic", return_value=0.0):
            lines = list(_fetch_run_logs_incrementally(run_id, mock_client, sleep_fn=mock_sleep, max_wait=10))

        # Verify we got the incremental lines
        assert "Terraform v1.7.0" in lines
        assert "Plan: 2 to add" in lines
        # Verify sleep was called between cycles
        assert mock_sleep.called

    def test_yields_apply_lines_after_plan(self):
        """Generator should transition from plan logs to apply logs."""
        run_id = "run-789"
        plan_id = "plan-111"
        apply_id = "apply-222"

        plan_logs = ["Terraform v1.7.0\nPlan: 1 to add"]
        apply_logs = ["Apply complete! Resources: 1 added\n"]

        # Simulate state transitions: planning → planned → applying → applied
        runs = [
            self._make_run(run_id, "planning", plan_id=plan_id),
            self._make_run(run_id, "planned", plan_id=plan_id),
            self._make_run(run_id, "applying", plan_id=plan_id, apply_id=apply_id),
            self._make_run(run_id, "applied", plan_id=plan_id, apply_id=apply_id),
        ]

        mock_client = MagicMock()
        mock_client.runs.get.side_effect = runs
        mock_client.runs.get_plan_logs.side_effect = plan_logs
        mock_client.runs.get_apply_logs.side_effect = apply_logs
        mock_sleep = MagicMock()

        lines = list(_fetch_run_logs_incrementally(run_id, mock_client, sleep_fn=mock_sleep, max_wait=10))

        # Should have both plan and apply lines
        assert len(lines) >= 2
        assert any("Plan:" in line for line in lines)
        assert any("Apply complete" in line for line in lines)

    def test_yields_nothing_when_no_plan_id(self):
        """Generator should yield nothing when run has no plan_id yet."""
        run_id = "run-pending"

        # Run is pending with no plan_id, then reaches terminal state
        runs = [
            self._make_run(run_id, "pending", plan_id=None),
            self._make_run(run_id, "pending", plan_id=None),
            self._make_run(run_id, "canceled", plan_id=None),  # Terminal state
        ]

        mock_client = MagicMock()
        mock_client.runs.get.side_effect = runs
        mock_sleep = MagicMock()

        lines = list(_fetch_run_logs_incrementally(run_id, mock_client, sleep_fn=mock_sleep, max_wait=10))

        # No logs should be emitted
        assert lines == []
        # But sleep should still be called (waiting for state change)
        assert mock_sleep.called

    def test_stops_when_run_is_terminal(self):
        """Generator should stop when run reaches a terminal state."""
        run_id = "run-error"
        plan_id = "plan-err"

        plan_logs = ["Error: Invalid configuration"]

        # Run enters errored state (terminal)
        runs = [
            self._make_run(run_id, "planning", plan_id=plan_id),
            self._make_run(run_id, "errored", plan_id=plan_id),
        ]

        mock_client = MagicMock()
        mock_client.runs.get.side_effect = runs
        mock_client.runs.get_plan_logs.side_effect = plan_logs
        mock_sleep = MagicMock()

        lines = list(_fetch_run_logs_incrementally(run_id, mock_client, sleep_fn=mock_sleep, max_wait=10))

        # Should have yielded error log, then stopped
        assert len(lines) > 0
        assert any("Error" in line for line in lines)
        # Should not have called sleep after terminal state
        # (last iteration doesn't sleep before checking terminal status)
        assert mock_client.runs.get.call_count == 2
