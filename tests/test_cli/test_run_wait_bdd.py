"""BDD tests for enhanced run lifecycle management."""

from unittest.mock import MagicMock, patch

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.run import Run, RunStatus
from terrapyne.models.workspace import Workspace

runner = CliRunner()


@scenario("../features/run_wait.feature", "Waiting for a run to complete")
def test_run_wait():
    pass


@scenario("../features/run_wait.feature", "Waiting for a busy queue")
def test_run_wait_queue():
    pass


@scenario("../features/run_wait.feature", "Clearing the queue before triggering")
def test_run_discard_older():
    pass


@scenario("../features/run_wait.feature", "Exiting with success when paused for approval")
def test_run_pause_success():
    pass


@given("a terraform cloud organization is accessible")
def terraform_org_ready():
    pass


@given(
    parsers.parse('a workspace "{workspace_name}" is ready for operations'),
    target_fixture="mock_client",
)
def workspace_ready(workspace_name):
    m = MagicMock()
    ws = Workspace.model_construct(id="ws-123", name=workspace_name)
    m.workspaces.get.return_value = ws
    m.get_organization.return_value = "test-org"
    return m


@given(parsers.parse('the workspace "{workspace_name}" has an active run "{run_id}"'))
def workspace_has_active_run(mock_client, workspace_name, run_id):
    active_run = Run.model_construct(id=run_id, status=RunStatus.PLANNING)
    mock_client.runs.get_active_runs.return_value = [active_run]

    # Poll for the busy run
    mock_client.runs.poll_until_complete.side_effect = [
        Run.model_construct(id=run_id, status=RunStatus.APPLIED),  # First call for wait_queue
        Run.model_construct(id="run-new", status=RunStatus.PLANNED),  # Second call for the new run
    ]

    # New run creation
    new_run = Run.model_construct(id="run-new", status=RunStatus.PENDING)
    mock_client.runs.create.return_value = new_run


@given(parsers.parse('the workspace "{workspace_name}" has several pending runs'))
def workspace_has_pending_runs(mock_client, workspace_name):
    pending_runs = [
        Run.model_construct(id="run-1", status=RunStatus.PENDING),
        Run.model_construct(id="run-2", status=RunStatus.PLAN_QUEUED),
    ]
    mock_client.runs.get_active_runs.return_value = pending_runs

    # New run
    new_run = Run.model_construct(id="run-new", status=RunStatus.PENDING)
    mock_client.runs.create.return_value = new_run
    mock_client.runs.poll_until_complete.return_value = Run.model_construct(
        id="run-new", status=RunStatus.PLANNED
    )


@given('the run reaches "planned" status')
def run_reaches_planned(mock_client):
    # Setup poll sequence to end at PLANNED
    final_run = Run.model_construct(id="run-123", status=RunStatus.PLANNED, plan_id="p-123")
    mock_client.runs.poll_until_complete.return_value = final_run
    mock_client.runs.get_plan.return_value = MagicMock(additions=1, changes=0, destructions=0)


@given("auto-apply is disabled")
def auto_apply_disabled(mock_client):
    # This is the default in our mock creation
    pass


@when(
    parsers.parse('I trigger a new plan for "{workspace_name}" with --wait'),
    target_fixture="cli_result",
)
def trigger_with_wait(mock_client, workspace_name):
    run = Run.model_construct(id="run-123", status=RunStatus.PENDING)
    mock_client.runs.create.return_value = run

    # If not already set by "the run reaches planned status"
    if not mock_client.runs.poll_until_complete.called:
        final_run = Run.model_construct(id="run-123", status=RunStatus.PLANNED, plan_id="p-123")
        mock_client.runs.poll_until_complete.return_value = final_run
        mock_client.runs.get_plan.return_value = MagicMock(additions=1, changes=0, destructions=0)

    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", workspace_name)
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["run", "trigger", workspace_name, "--wait", "-o", "test-org"])


@when(
    parsers.parse('I trigger a new plan for "{workspace_name}" with --wait-queue'),
    target_fixture="cli_result",
)
def trigger_wait_queue(mock_client, workspace_name):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", workspace_name)
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(
            app, ["run", "trigger", workspace_name, "--wait-queue", "-o", "test-org"]
        )


@when(
    parsers.parse('I trigger a new plan for "{workspace_name}" with --discard-older'),
    target_fixture="cli_result",
)
def trigger_discard_older(mock_client, workspace_name):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", workspace_name)
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(
            app, ["run", "trigger", workspace_name, "--discard-older", "-o", "test-org"]
        )


@then(parsers.parse('the command should block until the run is "{status}"'))
def command_blocks(cli_result, status):
    # The command has already run in the @when step
    # Match emoji and status name in the table
    assert status in cli_result.stdout
    assert "planned" in cli_result.stdout.lower() or "applied" in cli_result.stdout.lower()


@then("the command should exit with code 0")
def exit_zero(cli_result):
    assert cli_result.exit_code == 0


@then(parsers.parse('it should first wait for "{run_id}" to complete'))
def check_waited_for_run(mock_client, run_id, cli_result):
    # Check that poll_until_complete was called with the busy run ID
    mock_client.runs.poll_until_complete.assert_any_call(run_id)
    assert f"Waiting for current run {run_id}" in cli_result.stdout


@then("then it should trigger the new run")
def check_triggered_new(mock_client, cli_result):
    mock_client.runs.create.assert_called()
    assert "Created PLAN run" in cli_result.stdout or "Created DESTROY run" in cli_result.stdout


@then("all existing non-terminal runs should be discarded")
def check_discarded(mock_client):
    assert mock_client.runs.discard.call_count == 2
    mock_client.runs.discard.assert_any_call(
        "run-1", comment="Discarded by terrapyne --discard-older"
    )
    mock_client.runs.discard.assert_any_call(
        "run-2", comment="Discarded by terrapyne --discard-older"
    )


@then("the output should indicate it is paused for approval")
def check_paused_output(cli_result):
    assert "Run paused for manual approval" in cli_result.stdout
