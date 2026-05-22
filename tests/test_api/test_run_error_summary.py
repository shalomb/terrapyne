"""Tests for RunsAPI.get_error_summary — apply-log fallback when plan succeeds."""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.runs import RunsAPI
from terrapyne.models.run import Run


def _make_run(
    run_id: str,
    plan_id: str | None = "plan-abc",
    plan_status: str = "errored",
    apply_id: str | None = "apply-abc",
    message: str = "Triggered via CLI",
) -> Run:
    """Build a minimal errored Run for testing."""
    data: dict = {
        "id": run_id,
        "type": "runs",
        "attributes": {
            "status": "errored",
            "created-at": "2026-05-01T10:00:00Z",
            "updated-at": "2026-05-01T10:05:00Z",
            "message": message,
            "auto-apply": True,
            "is-destroy": False,
        },
        "relationships": {},
    }
    if plan_id:
        data["relationships"]["plan"] = {"data": {"id": plan_id, "type": "plans"}}
    if apply_id:
        data["relationships"]["apply"] = {"data": {"id": apply_id, "type": "applies"}}

    run = Run.from_api_response(data, included=[])
    # Inject plan status via included sideload simulation
    if plan_id:
        run = Run.from_api_response(
            data,
            included=[
                {
                    "id": plan_id,
                    "type": "plans",
                    "attributes": {
                        "status": plan_status,
                        "log-read-url": None,
                        "has-changes": True,
                        "resource-additions": 0,
                        "resource-changes": 0,
                        "resource-destructions": 0,
                        "resource-imports": 0,
                        "action-invocations": 0,
                    },
                }
            ],
        )
    return run


class TestGetErrorSummary:
    """RunsAPI.get_error_summary extracts the right log based on plan status."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        return RunsAPI(mock_client)

    # ------------------------------------------------------------------
    # Plan-stage failure
    # ------------------------------------------------------------------

    def test_plan_errored_fetches_plan_log(self, api, mock_client):
        """When plan status is errored, the error comes from the plan log."""
        run = _make_run("run-plan-fail", plan_status="errored")
        mock_client._request.return_value.text = (
            "Error: creating EC2 Instance: OptInRequired: not subscribed\n"
        )

        summary = api.get_error_summary(run)

        assert "OptInRequired" in summary
        # Only plan log fetched — apply log never called
        called_paths = [c.args[1] for c in mock_client._request.call_args_list]
        assert any("plans" in p and "logs" in p for p in called_paths)
        assert not any("applies" in p for p in called_paths)

    def test_plan_errored_strips_ansi(self, api, mock_client):
        """ANSI escape codes in logs are stripped from the summary."""
        run = _make_run("run-ansi", plan_status="errored")
        mock_client._request.return_value.text = (
            "\x1b[31mError: creating EC2 Instance: Forbidden\x1b[0m\n"
        )

        summary = api.get_error_summary(run)

        assert "\x1b" not in summary
        assert "Forbidden" in summary

    # ------------------------------------------------------------------
    # Apply-stage failure
    # ------------------------------------------------------------------

    def test_plan_finished_fetches_apply_log(self, api, mock_client):
        """When plan status is finished, the error comes from the apply log."""
        run = _make_run("run-apply-fail", plan_status="finished")
        mock_client._request.return_value.text = (
            "Error: creating RDS DB Subnet Group (tec-db-default-defra): "
            "DBSubnetGroupAlreadyExists\n"
        )

        summary = api.get_error_summary(run)

        assert "DBSubnetGroupAlreadyExists" in summary
        # Only apply log fetched — plan log never called
        called_paths = [c.args[1] for c in mock_client._request.call_args_list]
        assert any("applies" in p and "logs" in p for p in called_paths)
        assert not any("plans" in p and "logs" in p for p in called_paths)

    def test_plan_finished_multiple_errors_all_returned(self, api, mock_client):
        """All Error: lines from the apply log appear in the summary."""
        run = _make_run("run-multi", plan_status="finished")
        mock_client._request.return_value.text = (
            "module.at_TakedaRDS.aws_db_subnet_group.dr_subnet_group[0]: Creating...\n"
            "Error: creating RDS DB Subnet Group (tec-db-default-defra): DBSubnetGroupAlreadyExists\n"
            "Error: creating RDS DB Subnet Group (tec-db-default-euw1): DBSubnetGroupAlreadyExists\n"
        )

        summary = api.get_error_summary(run)

        assert "tec-db-default-defra" in summary
        assert "tec-db-default-euw1" in summary

    # ------------------------------------------------------------------
    # Fallback cases
    # ------------------------------------------------------------------

    def test_no_plan_id_returns_run_message(self, api, mock_client):
        """When the run has no plan relationship, fall back to run.message."""
        run = _make_run("run-no-plan", plan_id=None, apply_id=None, message="Triggered via UI")

        summary = api.get_error_summary(run)

        assert summary == "Triggered via UI"
        mock_client._request.assert_not_called()

    def test_empty_plan_log_returns_run_message(self, api, mock_client):
        """When the plan log is empty (e.g. 404), fall back to run.message."""
        run = _make_run("run-no-logs", plan_status="errored", message="Triggered via CLI")
        mock_client._request.return_value.text = ""

        summary = api.get_error_summary(run)

        assert summary == "Triggered via CLI"

    def test_plan_log_no_error_lines_returns_run_message(self, api, mock_client):
        """When plan log exists but has no Error: lines, fall back to run.message."""
        run = _make_run("run-warn-only", plan_status="errored", message="Deploy failed")
        mock_client._request.return_value.text = (
            "Warning: Deprecated argument 'foo' in resource bar\n"
            "Planning complete. Changes: 0 to add, 0 to change, 0 to destroy.\n"
        )

        summary = api.get_error_summary(run)

        assert summary == "Deploy failed"

    def test_empty_apply_log_falls_back_to_run_message(self, api, mock_client):
        """When plan finished but apply log is empty, fall back to run.message."""
        run = _make_run("run-empty-apply", plan_status="finished", message="Merge PR #42")
        mock_client._request.return_value.text = ""

        summary = api.get_error_summary(run)

        assert summary == "Merge PR #42"

    # ------------------------------------------------------------------
    # B6 — plan_status=None defensive fallback (apply log tried first)
    # ------------------------------------------------------------------

    def test_plan_status_none_with_apply_id_tries_apply_log(self, api, mock_client):
        """When plan_status is None but apply_id exists, try the apply log first.

        This covers the case where runs.get() was called without include=plan
        (B5) so plan_status is None, but the run errored during apply.
        """
        run = _make_run("run-none-status", plan_status=None, message="fix: VPC Lambda IAM")
        mock_client._request.return_value.text = (
            "Error: creating Lambda Function: InvalidParameterValueException: "
            "The provided execution role does not have permissions\n"
        )

        summary = api.get_error_summary(run)

        assert "InvalidParameterValueException" in summary
        called_paths = [c.args[1] for c in mock_client._request.call_args_list]
        assert any("applies" in p and "logs" in p for p in called_paths)

    def test_plan_status_none_empty_apply_log_falls_back_to_plan_log(self, api, mock_client):
        """When plan_status is None and apply log is empty, fall back to plan log.

        Verifies that apply log is tried first (order matters for B6 fix).
        """
        run = _make_run("run-none-fallback", plan_status=None, message="fallback msg")

        def fake_request(method, path, **_kwargs):
            m = MagicMock()
            m.text = "Error: plan stage error\n" if "plans" in path else ""
            return m

        mock_client._request.side_effect = fake_request

        summary = api.get_error_summary(run)

        assert "plan stage error" in summary
        # Apply log must have been tried before the plan log
        called_paths = [c.args[1] for c in mock_client._request.call_args_list]
        apply_idx = next((i for i, p in enumerate(called_paths) if "applies" in p), None)
        plan_idx = next((i for i, p in enumerate(called_paths) if "plans" in p), None)
        assert apply_idx is not None, "Apply log was never fetched"
        assert plan_idx is not None, "Plan log was never fetched"
        assert apply_idx < plan_idx, "Apply log must be tried before plan log"

    def test_pre_plan_failure_uses_archivist_url_via_get_plan(self, api, mock_client):
        """Pre-plan failure: get_error_summary fetches the Plan to get log_read_url (B7/B8)."""
        run = _make_run("run-pre-plan", plan_status="errored", apply_id=None)
        archivist_url = "https://archivist.terraform.io/v1/object/pre-plan"

        mock_client.get.return_value = {
            "data": {
                "id": "plan-abc",
                "type": "plans",
                "attributes": {
                    "status": "errored",
                    "log-read-url": archivist_url,
                    "has-changes": False,
                    "resource-additions": 0,
                    "resource-changes": 0,
                    "resource-destructions": 0,
                    "resource-imports": 0,
                    "action-invocations": 0,
                },
            }
        }

        def fake_request(method, path, **_kwargs):
            m = MagicMock()
            m.text = "Error: Invalid provider configuration\n" if path == archivist_url else ""
            return m

        mock_client._request.side_effect = fake_request

        summary = api.get_error_summary(run)

        assert "Invalid provider configuration" in summary
        called_paths = [c.args[1] for c in mock_client._request.call_args_list]
        assert any(p == archivist_url for p in called_paths)


class TestLogReadUrlFallback:
    """B7/B8: get_plan_logs and get_apply_logs fall back to log_read_url when streaming is empty."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        return RunsAPI(mock_client)

    def test_get_plan_logs_falls_back_to_log_read_url_when_streaming_empty(self, api, mock_client):
        """When /plans/{id}/logs returns empty, fetch log_read_url instead (B7/B8)."""
        archivist_url = "https://archivist.terraform.io/v1/object/abc"
        archivist_content = "Error: Invalid provider configuration\n"

        def fake_request(method, path, **_kwargs):
            m = MagicMock()
            m.text = archivist_content if path == archivist_url else ""
            return m

        mock_client._request.side_effect = fake_request

        result = api.get_plan_logs("plan-abc", log_read_url=archivist_url)

        assert result == archivist_content
        called_paths = [c.args[1] for c in mock_client._request.call_args_list]
        assert any("plans" in p and "logs" in p for p in called_paths), "streaming endpoint called"
        assert any(p == archivist_url for p in called_paths), "archivist fallback called"

    def test_get_plan_logs_no_fallback_when_streaming_has_content(self, api, mock_client):
        """When /plans/{id}/logs returns content, log_read_url is not fetched."""
        streaming_content = "Terraform will perform the following actions...\n"
        mock_client._request.return_value.text = streaming_content

        result = api.get_plan_logs(
            "plan-abc", log_read_url="https://archivist.terraform.io/v1/object/abc"
        )

        assert result == streaming_content
        assert mock_client._request.call_count == 1
        called_path = mock_client._request.call_args.args[1]
        assert "plans" in called_path and "logs" in called_path

    def test_get_plan_logs_no_fallback_when_no_log_read_url(self, api, mock_client):
        """When log_read_url is not provided and streaming is empty, return empty."""
        mock_client._request.return_value.text = ""

        result = api.get_plan_logs("plan-abc")

        assert result == ""
        assert mock_client._request.call_count == 1

    def test_get_apply_logs_falls_back_to_log_read_url_when_streaming_empty(self, api, mock_client):
        """When /applies/{id}/logs returns empty, fetch log_read_url instead (B7/B8)."""
        archivist_url = "https://archivist.terraform.io/v1/object/xyz"
        archivist_content = "Error: apply failed\n"

        def fake_request(method, path, **_kwargs):
            m = MagicMock()
            m.text = archivist_content if path == archivist_url else ""
            return m

        mock_client._request.side_effect = fake_request

        result = api.get_apply_logs("apply-abc", log_read_url=archivist_url)

        assert result == archivist_content
        called_paths = [c.args[1] for c in mock_client._request.call_args_list]
        assert any("applies" in p and "logs" in p for p in called_paths)
        assert any(p == archivist_url for p in called_paths)

    def test_get_apply_logs_no_fallback_when_streaming_has_content(self, api, mock_client):
        """When /applies/{id}/logs returns content, log_read_url is not fetched."""
        streaming_content = "Apply complete! Resources: 2 added.\n"
        mock_client._request.return_value.text = streaming_content

        result = api.get_apply_logs(
            "apply-abc", log_read_url="https://archivist.terraform.io/v1/object/xyz"
        )

        assert result == streaming_content
        assert mock_client._request.call_count == 1
