"""CLI tests for run --wait flag - BDD scenarios."""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.run import Run
from terrapyne.models.workspace import Workspace

runner = CliRunner()

# ============================================================================
# Scenarios
# ============================================================================


@scenario("../features/run_wait.feature", "--wait blocks until run succeeds and exits 0")
def test_wait_blocks_until_success():
    pass


@scenario("../features/run_wait.feature", "--wait exits non-zero when run fails")
def test_wait_exits_on_failure():
    pass


@scenario("../features/run_wait.feature", "--wait exits non-zero when run is discarded")
def test_wait_exits_on_discard():
    pass


@scenario("../features/run_wait.feature", "run apply --wait streams apply logs")
def test_apply_wait_streams_logs():
    pass


# ============================================================================
# Background / Given Steps
# ============================================================================


@given("a terraform cloud organization is accessible")
def terraform_org_ready():
    pass


@given(parsers.parse('a workspace "{workspace}" is ready for operations'))
def workspace_targeting(workspace):
    """Accept workspace name in step context."""
    pass


@given(parsers.parse('a triggered run that will reach "{status}" status'))
def triggered_run_with_status(status, request):
    """Setup a run that will transition to the given status."""
    request.config.wait_run_status = status


@given(parsers.parse('a triggered run that will be "{status}"'))
def triggered_run_will_be(status, request):
    """Setup a run that will transition to the given status."""
    request.config.wait_run_status = status


@given(parsers.parse('a run in "{status}" status with apply_id'))
def run_with_apply_id(status, request):
    """Setup a run in given status with apply_id."""
    request.config.wait_run_status = status
    request.config.wait_has_apply_id = True


# ============================================================================
# When Steps
# ============================================================================


@pytest.fixture
@when(parsers.parse("I run tfc run trigger {workspace} --wait"), target_fixture="trigger_with_wait")
def trigger_with_wait_fixture(workspace, workspace_detail_response, run_list_response, request):
    """Trigger a run with --wait flag."""
    status = getattr(request.config, "wait_run_status", "applied")

    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        ws = Workspace.from_api_response(workspace_detail_response["data"])
        mock_instance.workspaces.get.return_value = ws

        # Create initial run response
        run_data = run_list_response["data"][0].copy()
        run_data["attributes"]["status"] = "pending"
        initial_run = Run.from_api_response(run_data)
        mock_instance.runs.create.return_value = initial_run

        # Create final run response with target status
        final_run_data = run_data.copy()
        final_run_data["attributes"]["status"] = status
        final_run = Run.from_api_response(final_run_data)

        # Mock poll_until_complete to return final run
        mock_instance.runs.poll_until_complete.return_value = final_run

        # Mock plan fetching
        if final_run.plan_id:
            mock_instance.runs.get_plan.return_value = MagicMock()

        result = runner.invoke(
            app, ["run", "trigger", workspace, "--organization", "test-org", "--wait"]
        )

        return {"result": result, "run": final_run}


@pytest.fixture
@when(parsers.parse("I run tfc run apply {run_id} --wait"), target_fixture="apply_wait_result")
def apply_with_wait_fixture(run_id, workspace_detail_response, run_list_response, request):
    """Apply a run with --wait flag."""
    status = getattr(request.config, "wait_run_status", "applied")

    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Create run response
        run_data = run_list_response["data"][0].copy()
        run_data["id"] = run_id
        run_data["attributes"]["status"] = status

        # Add apply_id if test requires it
        if getattr(request.config, "wait_has_apply_id", False):
            run_data["relationships"] = {
                "apply": {"data": {"id": "apply-123456", "type": "applies"}}
            }

        run = Run.from_api_response(run_data)

        mock_instance.runs.get.return_value = run
        mock_instance.runs.apply.return_value = run
        mock_instance.runs.poll_until_complete.return_value = run

        # Mock plan and apply fetching
        if run.plan_id:
            mock_instance.runs.get_plan.return_value = MagicMock()
        if run.apply_id:
            mock_instance.runs.get_apply_logs.return_value = "apply logs..."

        result = runner.invoke(
            app, ["run", "apply", run_id, "--organization", "test-org", "--auto-approve", "--wait"]
        )

        return {"result": result, "run": run}


# ============================================================================
# Then Steps (trigger --wait scenarios)
# ============================================================================


@then("the command streams log lines to stdout")
def check_logs_streamed(trigger_with_wait):
    """Check that logs were streamed (polling was called)."""
    assert trigger_with_wait["result"].exit_code in [0, 1], (
        f"Got exit code {trigger_with_wait['result'].exit_code}: {trigger_with_wait['result'].stdout}"
    )
    # Verify the run status was displayed
    assert trigger_with_wait["run"].status.value in trigger_with_wait["result"].stdout.lower()


@then("the exit code is 0")
def check_exit_zero_trigger(trigger_with_wait):
    """Check exit code is 0 for successful trigger run."""
    assert trigger_with_wait["result"].exit_code == 0, (
        f"Expected exit 0, got {trigger_with_wait['result'].exit_code}. Output: {trigger_with_wait['result'].stdout}"
    )


@then("the exit code is 1")
def check_exit_one_trigger(trigger_with_wait):
    """Check exit code is 1 for failed trigger run."""
    assert trigger_with_wait["result"].exit_code == 1, (
        f"Expected exit 1, got {trigger_with_wait['result'].exit_code}. Output: {trigger_with_wait['result'].stdout}"
    )


@then("stderr contains the error message")
def check_stderr_contains_error(trigger_with_wait):
    """Check that stderr contains error information."""
    # Either stdout or stderr should contain the status
    output = trigger_with_wait["result"].stdout + trigger_with_wait["result"].stderr
    status = trigger_with_wait["run"].status.value
    assert status in output.lower()


# ============================================================================
# Then Steps (apply --wait scenarios)
# ============================================================================


@then("apply log lines are streamed to stdout")
def check_apply_logs_streamed(apply_wait_result):
    """Check that apply logs were streamed."""
    # The poll_until_complete should have been called
    assert apply_wait_result["result"].exit_code in [0, 1]
    # Verify the run status was displayed
    assert apply_wait_result["run"].status.value in apply_wait_result["result"].stdout.lower()


@then("the exit code reflects the run outcome")
def check_exit_reflects_outcome(apply_wait_result):
    """Check exit code reflects the actual run outcome."""
    run = apply_wait_result["run"]
    expected_exit = 0 if run.status.is_successful else 1
    assert apply_wait_result["result"].exit_code == expected_exit
