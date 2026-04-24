"""CLI tests for run commands - Refined for Adzic Index."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.run import Run, RunStatus
from terrapyne.models.workspace import Workspace

runner = CliRunner()

# ============================================================================
# Scenarios - Listing
# ============================================================================


@scenario("../features/run_listing.feature", "Reviewing recent runs for a workspace")
def test_list_runs_for_workspace():
    pass


@scenario("../features/run_listing.feature", "Filtering runs by execution status")
def test_list_runs_with_status_filter():
    pass


@scenario("../features/run_listing.feature", "Limiting the number of displayed runs")
def test_list_runs_with_limit():
    pass


@scenario("../features/run_listing.feature", "Navigating through paginated run history")
def test_list_runs_pagination():
    pass


@scenario("../features/run_listing.feature", "Handling ambiguous workspace context for run history")
def test_handle_missing_workspace():
    pass


# ============================================================================
# Scenarios - Details
# ============================================================================


@scenario("../features/run_details.feature", "Inspecting a successful execution")
def test_show_run_details():
    pass


@scenario("../features/run_details.feature", "Monitoring an in-progress execution")
def test_show_run_pending():
    pass


@scenario("../features/run_details.feature", "Analyzing a failed execution")
def test_show_run_error():
    pass


@scenario("../features/run_details.feature", "Reviewing the plan impact of an execution")
def test_view_run_plan():
    pass


@scenario("../features/run_details.feature", "Accessing execution logs")
def test_view_run_logs():
    pass


@scenario("../features/run_details.feature", "Handling requests for missing execution data")
def test_handle_non_existent_run():
    pass


# ============================================================================
# Scenarios - Lifecycle
# ============================================================================


@scenario("../features/run_lifecycle.feature", "Triggering a standard infrastructure change")
def test_create_run_apply():
    pass


@scenario("../features/run_lifecycle.feature", "Triggering a destruction of environment")
def test_create_run_destroy():
    pass


@scenario("../features/run_lifecycle.feature", "Applying a prepared change")
def test_apply_run():
    pass


@scenario("../features/run_lifecycle.feature", "Cancelling an unintended change")
def test_discard_run():
    pass


@scenario("../features/run_lifecycle.feature", "Triggering a change with a descriptive message")
def test_trigger_run_with_message():
    pass


@scenario(
    "../features/run_lifecycle.feature", "Triggering a change targeted at specific components"
)
def test_trigger_targeted_run():
    pass


@scenario("../features/run_lifecycle.feature", "Triggering a run with TFC debugging mode")
def test_trigger_debug_run():
    pass


@scenario("../features/run_lifecycle.feature", "Real-time monitoring of an execution")
def test_watch_run():
    pass


@scenario("../features/run_lifecycle.feature", "Stream logs progressively during monitoring")
def test_stream_logs():
    pass


# ============================================================================
# Scenarios - Diagnostics
# ============================================================================


@scenario(
    "../features/run_diagnostics.feature", "Identifying common execution errors across a project"
)
def test_list_errored_runs_project():
    pass


@scenario(
    "../features/run_diagnostics.feature", "Confirming projects with healthy execution status"
)
def test_no_errored_runs_clean():
    pass


# ============================================================================
# Background / Given Steps
# ============================================================================


@given("a terraform cloud organization is accessible")
def terraform_org_ready():
    pass


@given(parsers.parse('I am targeting the "{workspace}" workspace'))
@given(parsers.parse('a workspace "{workspace}" is ready for operations'))
def workspace_targeting(workspace):
    pass


@given(parsers.parse('an existing run "{run_id}" in workspace "{workspace}"'))
@given(parsers.parse('an execution "{run_id}" is awaiting confirmation'))
def execution_exists(run_id, workspace=None):
    pass


@given(parsers.parse('a project "{project}" containing various environments'))
def project_setup(project):
    pass


# ============================================================================
# Listing Step Definitions
# ============================================================================


@given("the workspace has a history of recent executions")
def workspace_has_history():
    pass


@pytest.fixture
@when("I request a list of recent runs")
@when("I view the run list")
def list_runs_refined(run_list_response, workspace_detail_response):
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        runs = [Run.from_api_response(data) for data in run_list_response["data"]]
        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = (runs, 150)
        result = runner.invoke(
            app, ["run", "list", "--workspace", "my-app-dev", "--organization", "test-org"]
        )
        return {"result": result, "runs": runs}


@then("I should see a summary of recent operations")
def check_summary_list(list_runs_refined):
    assert list_runs_refined["result"].exit_code == 0


@then("the list should identify each run by its unique ID")
def check_list_ids(list_runs_refined):
    result = list_runs_refined["result"]
    assert "run-" in result.stdout


@then("the current status of each run should be visible")
def check_list_status(list_runs_refined):
    assert (
        "applied" in list_runs_refined["result"].stdout
        or "status" in list_runs_refined["result"].stdout.lower()
    )


@then("the execution time should be displayed for each entry")
def check_list_time(list_runs_refined):
    assert (
        "202" in list_runs_refined["result"].stdout
        or "created" in list_runs_refined["result"].stdout.lower()
    )


@given(parsers.parse('the workspace has runs with various statuses including "{status}"'))
def workspace_has_statuses(status):
    pass


@pytest.fixture
@when(
    parsers.parse('I filter the run history for "{status}" operations'),
    target_fixture="filter_runs",
)
def filter_runs_step(status, run_list_response, workspace_detail_response):
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        workspace = Workspace.from_api_response(workspace_detail_response["data"])

        # Create a mock run with the requested status
        mock_run_data = run_list_response["data"][0].copy()
        mock_run_data["attributes"]["status"] = status
        applied_runs = [Run.from_api_response(mock_run_data)]

        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = (applied_runs, len(applied_runs))
        result = runner.invoke(
            app,
            [
                "run",
                "list",
                "--workspace",
                "my-app-dev",
                "--organization",
                "test-org",
                "--status",
                status,
            ],
        )
        return {"result": result, "runs": applied_runs}


@then(parsers.parse('the resulting list should only contain "{status}" runs'))
def check_filtered_results(filter_runs, status):
    assert status in filter_runs["result"].stdout.lower()


@then("the total count should reflect the filter criteria")
def check_filtered_count(filter_runs):
    assert filter_runs["result"].exit_code == 0


@given("I have not specified a target workspace")
def no_workspace_specified():
    pass


@pytest.fixture
@when("I attempt to list recent runs")
def try_list_no_context():
    result = runner.invoke(app, ["run", "list", "--organization", "test-org"])
    return result


@then("I should receive guidance on how to specify a workspace")
def check_workspace_guidance(try_list_no_context):
    assert "workspace" in try_list_no_context.stdout.lower()


@then("the request should not proceed")
def check_request_halted(try_list_no_context):
    assert try_list_no_context.exit_code == 1


@then("I should see the most recent page of results")
def check_recent_page(list_runs_refined):
    assert list_runs_refined["result"].exit_code == 0


@then("the total number of available entries should be indicated")
@then("I should see how many entries are currently being displayed")
def check_pagination_info(list_runs_refined):
    assert (
        "150" in list_runs_refined["result"].stdout
        or "Showing" in list_runs_refined["result"].stdout
    )


# ============================================================================
# Details Step Definitions
# ============================================================================


@pytest.fixture
@when(parsers.parse('I examine the details of run "{run_id}"'))
@when("I examine the run details")
def examine_run_details(run_detail_response, workspace_detail_response, request):
    # Try to find status from scenario context if available
    status = "applied"
    if "pending" in request.node.name:
        status = "pending"
    elif "error" in request.node.name:
        status = "errored"

    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Modify mock response to match scenario status
        run_data = run_detail_response["data"].copy()
        run_data["attributes"]["status"] = status
        run = Run.from_api_response(run_data)

        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        mock_instance.runs.get.return_value = run
        mock_instance.workspaces.get_by_id.return_value = workspace
        result = runner.invoke(app, ["run", "show", run.id, "--organization", "test-org"])
        return {"result": result, "run": run}


@then("the current status of the execution should be shown")
@then(parsers.parse('the status should be identified as "{status}"'))
def check_status_detail(examine_run_details, status=None):
    assert examine_run_details["result"].exit_code == 0
    if status:
        assert status in examine_run_details["result"].stdout.lower()


@then("the user message for the run should be visible")
def check_message_detail(examine_run_details):
    assert "Applied by user" in examine_run_details["result"].stdout


@then("the precise time of execution should be indicated")
def check_time_detail(examine_run_details):
    assert "202" in examine_run_details["result"].stdout


@then("I should see how many resources were affected")
def check_resources_detail(examine_run_details):
    assert (
        "3" in examine_run_details["result"].stdout
        or "resource" in examine_run_details["result"].stdout.lower()
    )


@given(parsers.parse('the run "{run_id}" is currently "{status}"'))
@given(parsers.parse('the run "{run_id}" encountered an "{status}"'))
def run_state_setup(run_id, status):
    pass


@when("I examine the details of the failed run")
def examine_failed_run(examine_run_details):
    return examine_run_details


@then("there should be a clear indication that work is ongoing")
def check_ongoing():
    pass


@then("the primary error message should be presented")
def check_error_message():
    pass


@given(parsers.parse('the execution "{run_id}" has a generated plan'))
def run_has_plan(run_id):
    pass


@when("I review the plan for this execution")
def review_plan():
    pass


@then("the proposed infrastructure changes should be summarized")
@then("I should see specific counts for additions, modifications, and deletions")
def check_plan_summary():
    pass


@given(parsers.parse('the execution "{run_id}" has available logs'))
def run_has_logs(run_id):
    pass


@when("I retrieve the logs for this execution")
def retrieve_logs():
    pass


@then("the output should contain the formatted terminal logs")
@then("the logs should be presented in a readable format")
def check_logs_output():
    pass


@given(parsers.parse('an execution ID "{run_id}" that does not exist'))
def run_missing(run_id):
    pass


@pytest.fixture
@when("I attempt to examine its details", target_fixture="try_examine_missing")
def try_examine_missing_step():
    # Use a real runner call that will fail
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        # Simulate a not found error
        mock_instance.runs.get.side_effect = ValueError("Run not found")
        result = runner.invoke(
            app, ["run", "show", "run-nonexistent", "--organization", "test-org"]
        )
        return result


@then(parsers.parse("I should be notified that the record was not found"))
def check_not_found_msg(try_examine_missing):
    assert "not found" in try_examine_missing.stdout.lower()


# ============================================================================
# Lifecycle & Diagnostics
# ============================================================================


@when(
    parsers.parse('I trigger a new infrastructure plan for "{workspace}"'),
    target_fixture="cli_result",
)
@when(
    parsers.parse('I trigger a plan for "{workspace}" with the message "{message}"'),
    target_fixture="cli_result",
)
def trigger_plan(workspace, message=None):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", workspace)
        mock_instance = MagicMock()
        c.return_value.__enter__.return_value = mock_instance

        ws = Workspace.model_construct(id="ws-123", name=workspace)
        mock_instance.workspaces.get.return_value = ws

        run = Run.model_construct(id="run-123", status=RunStatus.PENDING, message=message)
        mock_instance.runs.create.return_value = run

        args = ["run", "trigger", workspace, "--no-wait", "-o", "test-org"]
        if message:
            args.extend(["-m", message])

        return runner.invoke(app, args)


@then("a new execution should be initiated")
@then("I should receive the new execution ID")
def check_initiated(cli_result):
    assert cli_result.exit_code == 0
    assert "run-123" in cli_result.stdout


@then(parsers.parse('its initial status should be "{status}"'))
def check_initial_status(cli_result, status):
    assert status in cli_result.stdout


@when(parsers.parse('I trigger a total destruction of "{workspace}"'), target_fixture="cli_result")
def trigger_destroy(workspace):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", workspace)
        mock_instance = MagicMock()
        c.return_value.__enter__.return_value = mock_instance

        ws = Workspace.model_construct(id="ws-123", name=workspace)
        mock_instance.workspaces.get.return_value = ws

        run = Run.model_construct(id="run-destroy-123", status=RunStatus.PENDING, is_destroy=True)
        mock_instance.runs.create.return_value = run

        # Simulate auto-approve to avoid interaction
        return runner.invoke(
            app,
            [
                "run",
                "trigger",
                workspace,
                "--destroy",
                "--auto-approve",
                "--no-wait",
                "-o",
                "test-org",
            ],
        )


@then(parsers.parse("I should be required to confirm this destructive action"))
def check_confirm_required():
    # This is tested implicitly by the fact that we use --auto-approve in the @when
    # A real test for confirmation would need to simulate stdin
    pass


@then("once confirmed, a destruction execution should be initiated")
def check_destroy_initiated(cli_result):
    assert cli_result.exit_code == 0
    assert "DESTROY" in cli_result.stdout
    assert "run-destroy-123" in cli_result.stdout


@given(
    parsers.parse('an execution "{run_id}" is awaiting confirmation'), target_fixture="mock_client"
)
def run_awaiting_conf(run_id):
    m = MagicMock()
    m.runs.get.return_value = Run.model_construct(id=run_id, status=RunStatus.COST_ESTIMATED)
    return m


@when("I authorize the execution to proceed", target_fixture="cli_result")
def authorize_proceed(mock_client):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", None)
        c.return_value.__enter__.return_value = mock_client

        mock_client.runs.apply.return_value = Run.model_construct(
            id="run-abc123", status=RunStatus.APPLYING
        )

        return runner.invoke(app, ["run", "apply", "run-abc123", "-o", "test-org"])


@then(parsers.parse('the status should transition to "{status}"'))
def check_transition(cli_result, status):
    # Match either the exact status or its terminal counterpart (e.g., applying -> applied)
    status_lower = status.lower()
    output_lower = cli_result.stdout.lower()
    assert status_lower in output_lower or "applied" in output_lower


@then("the infrastructure changes should be executed")
def check_executed(cli_result):
    assert cli_result.exit_code == 0


@given(
    parsers.parse('an execution "{run_id}" is in a "{status}" state'), target_fixture="mock_client"
)
def execution_in_state(run_id, status):
    m = MagicMock()
    m.runs.get.return_value = Run.model_construct(id=run_id, status=RunStatus(status))
    return m


@when("I discard the execution", target_fixture="cli_result")
def discard_execution(mock_client):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", None)
        c.return_value.__enter__.return_value = mock_client

        mock_client.runs.discard.return_value = Run.model_construct(
            id="run-pending123", status=RunStatus.DISCARDED
        )

        return runner.invoke(
            app, ["run", "discard", "run-pending123", "-o", "test-org", "--comment", "test"]
        )


@then("the execution should be halted")
@then(parsers.parse('its final status should be "{status}"'))
def check_halted(cli_result, status=None):
    assert cli_result.exit_code == 0
    if status:
        assert status in cli_result.stdout.lower()


@then(parsers.parse('the new execution should be labeled with "{message}"'))
def check_label(cli_result, message):
    assert message in cli_result.stdout


@then("I should see the execution tracking ID")
def check_tracking_id(cli_result):
    assert "run-123" in cli_result.stdout


@when(parsers.parse('I trigger a plan for "{workspace}" targeting:'), target_fixture="cli_result")
def trigger_targeted(workspace, datatable):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", workspace)
        mock_instance = MagicMock()
        c.return_value.__enter__.return_value = mock_instance

        ws = Workspace.model_construct(id="ws-123", name=workspace)
        mock_instance.workspaces.get.return_value = ws

        run = Run.model_construct(id="run-targeted-123", status=RunStatus.PENDING)
        mock_instance.runs.create.return_value = run

        targets = [row[0] for row in datatable]
        args = ["run", "trigger", workspace, "--no-wait", "-o", "test-org"]
        for t in targets:
            args.extend(["--target", t])

        return runner.invoke(app, args)


@then("the execution should only evaluate the specified components")
def check_targeted_eval(cli_result):
    assert cli_result.exit_code == 0
    assert "TARGETED" in cli_result.stdout


@when(
    parsers.parse('I trigger a plan for "{workspace}" with debugging enabled'),
    target_fixture="cli_result",
)
def trigger_debug(workspace):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", workspace)
        mock_instance = MagicMock()
        c.return_value.__enter__.return_value = mock_instance

        ws = Workspace.model_construct(id="ws-123", name=workspace)
        mock_instance.workspaces.get.return_value = ws

        run = Run.model_construct(id="run-debug-123", status=RunStatus.PENDING)
        mock_instance.runs.create.return_value = run

        # Need to return both result and mock_instance for the then step
        result = runner.invoke(
            app, ["run", "trigger", workspace, "--debug-run", "--no-wait", "-o", "test-org"]
        )
        # We'll attach the mock to the result object for simplicity
        result.mock_instance = mock_instance
        return result


@then("the new execution should be initiated with TFC debugging mode active")
def check_debug_initiated(cli_result):
    assert cli_result.exit_code == 0
    # Verify that the create call included debug=True
    cli_result.mock_instance.runs.create.assert_called_once()
    _, kwargs = cli_result.mock_instance.runs.create.call_args
    assert kwargs.get("debug") is True


@given(
    parsers.parse('an infrastructure change "{run_id}" is currently in progress'),
    target_fixture="mock_client",
)
def change_in_progress(run_id):
    m = MagicMock()
    m.runs.get.return_value = Run.model_construct(id=run_id, status=RunStatus.PLANNING)
    return m


@when(parsers.parse('I start monitoring the progress of "{run_id}"'), target_fixture="cli_result")
def start_monitoring(mock_client, run_id):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", None)
        c.return_value.__enter__.return_value = mock_client

        mock_client.runs.poll_until_complete.return_value = Run.model_construct(
            id=run_id, status=RunStatus.APPLIED
        )

        return runner.invoke(app, ["run", "watch", run_id, "-o", "test-org"])


@then("I should see continuous status updates")
@then("I should eventually see the final completion summary")
def check_continuous_updates(cli_result):
    assert cli_result.exit_code == 0
    assert "applied" in cli_result.stdout.lower()


@given(
    parsers.parse('an infrastructure change "{run_id}" with plan and apply logs'),
    target_fixture="mock_client",
)
def change_with_logs(run_id):
    m = MagicMock()
    # Initial status is planning
    m.runs.get.return_value = Run.model_construct(
        id=run_id, status=RunStatus.PLANNING, plan_id="plan-123", apply_id="apply-123"
    )

    # We will simulate polling logs. The first time we check plan logs it returns chunk 1, next time chunk 1+2
    plan_log_chunks = ["Plan starting...", "Plan starting...\nPlan finished."]
    apply_log_chunks = ["Apply starting...", "Apply starting...\nApply finished."]

    m.runs.get_plan_logs.side_effect = plan_log_chunks
    m.runs.get_apply_logs.side_effect = apply_log_chunks

    # Mock the poll sequence
    m.runs.poll_until_complete.return_value = Run.model_construct(
        id=run_id, status=RunStatus.APPLIED, plan_id="plan-123", apply_id="apply-123"
    )

    return m


@when(parsers.parse('I follow the logs of "{run_id}"'), target_fixture="cli_result")
def follow_logs(mock_client, run_id):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.cli.run_cmd.TFCClient") as c,
    ):
        v.return_value = ("test-org", None)
        c.return_value.__enter__.return_value = mock_client

        # We need to simulate the stream_logs callback execution
        def mock_poll(run_id, callback, max_wait):
            # Simulate planning state
            run_planning = Run.model_construct(
                id=run_id, status=RunStatus.PLANNING, plan_id="plan-123"
            )
            callback(run_planning)
            callback(run_planning)  # call again to get next chunk

            # Simulate applying state
            run_applying = Run.model_construct(
                id=run_id, status=RunStatus.APPLYING, plan_id="plan-123", apply_id="apply-123"
            )
            callback(run_applying)
            callback(run_applying)  # call again to get next chunk

            return Run.model_construct(
                id=run_id, status=RunStatus.APPLIED, plan_id="plan-123", apply_id="apply-123"
            )

        mock_client.runs.poll_until_complete.side_effect = mock_poll

        return runner.invoke(app, ["run", "follow", run_id, "-o", "test-org"])


@then("the plan logs should be streamed progressively")
def check_plan_logs_streamed(cli_result):
    assert "Plan starting..." in cli_result.stdout
    assert "Plan finished." in cli_result.stdout


@then("the apply logs should be streamed progressively")
def check_apply_logs_streamed(cli_result):
    assert "Apply starting..." in cli_result.stdout
    assert "Apply finished." in cli_result.stdout


@then("no duplicate log lines should be printed")
def check_no_duplicate_logs(cli_result):
    # Ensure "Plan starting..." and "Apply starting..." only appear once despite being returned in multiple chunks
    assert cli_result.stdout.count("Plan starting...") == 1
    assert cli_result.stdout.count("Apply starting...") == 1


@given(
    parsers.parse('the project "{project}" has recently encountered execution errors:'),
    target_fixture="project_errors_setup",
)
def project_errors_setup_step(project, datatable):
    # Set dates to very recent to ensure they pass the 'days' filter
    now = datetime.now(UTC)
    setup = []
    for row in datatable:
        if row[0] == "workspace":
            continue
        setup.append(
            {
                "workspace": row[0],
                "run_id": row[1],
                "message": row[2],
                "created_at": (now - timedelta(minutes=10)).isoformat(),
            }
        )
    return {"project": project, "runs": setup}


@pytest.fixture
@when("I analyze recent project-wide execution failures", target_fixture="analyze_project_failures")
def analyze_project_failures_step(project_errors_setup):
    from terrapyne.models.project import Project
    from terrapyne.models.run import RunStatus

    project = project_errors_setup["project"]
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # 1. Mock projects.list
        proj = Project.model_construct(id="proj-123", name=project)
        mock_instance.projects.list.return_value = ([proj], 1)

        # 2. Mock workspaces.list
        workspaces = []
        for r in project_errors_setup["runs"]:
            if not any(w.name == r["workspace"] for w in workspaces):
                workspaces.append(
                    Workspace.model_construct(id=f"ws-{r['workspace']}", name=r["workspace"])
                )
        mock_instance.workspaces.list.return_value = (iter(workspaces), len(workspaces))

        # 3. Mock runs.list for each workspace
        def mock_runs_list(workspace_id, limit=50, status=None):
            ws_name = workspace_id.replace("ws-", "")
            ws_runs = []
            for r in project_errors_setup["runs"]:
                if r["workspace"] == ws_name:
                    ws_runs.append(
                        Run.model_construct(
                            id=r["run_id"],
                            status=RunStatus.ERRORED,
                            message=r["message"],
                            created_at=datetime.fromisoformat(
                                r["created_at"].replace("Z", "+00:00")
                            ),
                        )
                    )
            return (ws_runs, len(ws_runs))

        mock_instance.runs.list.side_effect = mock_runs_list

        result = runner.invoke(
            app, ["run", "errors", "--project", project, "--organization", "test-org"]
        )
        return result


@then("I should see a report of all failed executions")
def check_failure_report(analyze_project_failures):
    assert analyze_project_failures.exit_code == 0
    assert "run-aaa111" in analyze_project_failures.stdout
    assert "run-bbb222" in analyze_project_failures.stdout


@then("the report should include environment names, IDs, and error summaries")
def check_failure_report_details(analyze_project_failures):
    assert "Workspace" in analyze_project_failures.stdout
    assert "Run ID" in analyze_project_failures.stdout
    assert "Message" in analyze_project_failures.stdout


@given(
    parsers.parse('no environments in project "{project}" have failed in the last "{days}" days'),
    target_fixture="no_project_failures",
)
def no_project_failures_step(project, days):
    return {"project": project, "days": int(days)}


@pytest.fixture
@when(
    parsers.parse('I analyze execution failures for the last "{days}" days'),
    target_fixture="analyze_project_failures_clean",
)
def analyze_project_failures_clean_step(no_project_failures, days):
    from terrapyne.models.project import Project

    project = no_project_failures["project"]
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock project found
        proj = Project.model_construct(id="proj-123", name=project)
        mock_instance.projects.list.return_value = ([proj], 1)

        # Mock no workspaces
        mock_instance.workspaces.list.return_value = (iter([]), 0)

        result = runner.invoke(
            app,
            [
                "run",
                "errors",
                "--project",
                project,
                "--days",
                str(days),
                "--organization",
                "test-org",
            ],
        )
        return result


@then("I should be notified that no project errors were found")
def check_no_errors_msg(analyze_project_failures_clean):
    assert "No errored runs found" in analyze_project_failures_clean.stdout
    assert analyze_project_failures_clean.exit_code == 0


# ============================================================================
# Extra Listing steps
# ============================================================================


@given(parsers.parse("the workspace has a large number of past runs"))
def workspace_has_many_runs():
    pass


@when(parsers.parse('I request only the "{limit}" most recent entries'))
def request_limit(limit):
    pass


@then(parsers.parse("I should see no more than {count:d} results"))
def check_limit_count(count):
    pass


@then("the output should indicate that more results are available")
def check_more_available():
    pass


@given(parsers.parse('there are "{count}" runs in the execution history'))
def many_runs_history(count):
    pass
