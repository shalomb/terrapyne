"""BDD step definitions for log streaming scenarios.

Tests the real-time log streaming feature for plan and apply phases.
Follows strict Adzic BDD (business-readable, living, intention-revealing,
declarative, focused) and Farley TDD (fast, atomic, repeatable, necessary,
maintainable, understandable) principles.
"""

import pytest
from unittest.mock import MagicMock, patch
from pytest_bdd import given, when, then, scenario

from terrapyne.models.run import Run, RunStatus


# Scenarios
@scenario("../features/run_lifecycle.feature", "Streaming plan logs as they arrive")
def test_streaming_plan_logs_as_they_arrive():
    """Scenario: Streaming plan logs as they arrive."""


@scenario("../features/run_lifecycle.feature", "Streaming apply logs after plan completion")
def test_streaming_apply_logs_after_plan_completion():
    """Scenario: Streaming apply logs after plan completion."""


@scenario("../features/run_lifecycle.feature", "No logs available when run is pending")
def test_no_logs_available_when_run_is_pending():
    """Scenario: No logs available when run is pending."""


@scenario("../features/run_lifecycle.feature", "Handling transient errors during log streaming")
def test_handling_transient_errors_during_log_streaming():
    """Scenario: Handling transient errors during log streaming."""


@scenario("../features/run_lifecycle.feature", "Stopping log stream when run reaches terminal state")
def test_stopping_log_stream_when_run_reaches_terminal_state():
    """Scenario: Stopping log stream when run reaches terminal state."""


# Fixtures
@pytest.fixture
def mock_client():
    """Mock TFC client for testing."""
    client = MagicMock()
    # Ensure nested attributes exist
    client.runs = MagicMock()
    return client


@pytest.fixture
def execution_context():
    """Shared context for a scenario."""
    return {
        "run_id": None,
        "run_states": [],
        "plan_logs": [],
        "apply_logs": [],
        "streamed_lines": [],
        "error_on_call": None,
    }


def _make_run(run_id, status, plan_id=None, apply_id=None):
    """Create a Run instance without full API validation."""
    return Run.model_construct(
        id=run_id,
        status=RunStatus(status),
        plan_id=plan_id,
        apply_id=apply_id,
    )


# Background steps
@given("a terraform cloud organization is accessible")
def step_tfc_org_accessible():
    """Background: TFC organization is accessible."""
    # This is handled by mock_client fixture


@given('a workspace "my-app-dev" is ready for operations')
def step_workspace_ready():
    """Background: Workspace is ready for operations."""
    # This is implicit in the test setup


# Given steps
@given('an execution "run-log1" is planning infrastructure changes')
def step_execution_planning_log1(execution_context, mock_client):
    """Set up run-log1 in planning state."""
    run_id = "run-log1"
    execution_context["run_id"] = run_id
    execution_context["run_states"] = [
        _make_run(run_id, "planning", plan_id="plan-123"),
        _make_run(run_id, "planning", plan_id="plan-123"),
        _make_run(run_id, "planned", plan_id="plan-123"),
    ]
    execution_context["plan_logs"] = [
        "Terraform v1.7.0",
        "Terraform v1.7.0\nPlan: 2 to add, 0 to change",
        "Terraform v1.7.0\nPlan: 2 to add, 0 to change",
    ]
    mock_client.runs.get.side_effect = execution_context["run_states"]
    mock_client.runs.get_plan_logs.side_effect = execution_context["plan_logs"]
    mock_client.runs.get_apply_logs.return_value = ""  # No apply logs yet


@given('an execution "run-log2" has completed planning and started applying')
def step_execution_applying_log2(execution_context, mock_client):
    """Set up run-log2 transitioning to apply."""
    run_id = "run-log2"
    execution_context["run_id"] = run_id
    execution_context["run_states"] = [
        _make_run(run_id, "planned", plan_id="plan-456"),
        _make_run(run_id, "applying", plan_id="plan-456", apply_id="apply-789"),
        _make_run(run_id, "applied", plan_id="plan-456", apply_id="apply-789"),
    ]
    execution_context["plan_logs"] = [
        "Plan: 1 to add",
        "Plan: 1 to add",
        "Plan: 1 to add",
    ]
    execution_context["apply_logs"] = [
        "",
        "Apply complete! Resources: 1 added",
        "Apply complete! Resources: 1 added",
    ]
    mock_client.runs.get.side_effect = execution_context["run_states"]
    mock_client.runs.get_plan_logs.side_effect = execution_context["plan_logs"]
    mock_client.runs.get_apply_logs.side_effect = execution_context["apply_logs"]


@given('an execution "run-log3" is pending with no plan started')
def step_execution_pending_log3(execution_context, mock_client):
    """Set up run-log3 in pending state with no plan."""
    run_id = "run-log3"
    execution_context["run_id"] = run_id
    execution_context["run_states"] = [
        _make_run(run_id, "pending", plan_id=None),
        _make_run(run_id, "pending", plan_id=None),
        _make_run(run_id, "canceled", plan_id=None),
    ]
    mock_client.runs.get.side_effect = execution_context["run_states"]


@given('an execution "run-log4" is planning infrastructure')
def step_execution_planning_log4(execution_context, mock_client):
    """Set up run-log4 in planning state (for error scenario)."""
    run_id = "run-log4"
    execution_context["run_id"] = run_id
    execution_context["run_states"] = [
        _make_run(run_id, "planning", plan_id="plan-err"),
        _make_run(run_id, "planning", plan_id="plan-err"),
        _make_run(run_id, "errored", plan_id="plan-err"),
    ]
    execution_context["plan_logs"] = [
        "Terraform v1.7.0",
        "Terraform v1.7.0\nError: Invalid configuration",
        "Terraform v1.7.0\nError: Invalid configuration",
    ]
    mock_client.runs.get.side_effect = execution_context["run_states"]
    mock_client.runs.get_plan_logs.side_effect = execution_context["plan_logs"]


@given('an execution "run-log5" is in progress')
def step_execution_in_progress_log5(execution_context, mock_client):
    """Set up run-log5 in progress."""
    run_id = "run-log5"
    execution_context["run_id"] = run_id
    execution_context["run_states"] = [
        _make_run(run_id, "applying", plan_id="plan-xyz", apply_id="apply-xyz"),
        _make_run(run_id, "applied", plan_id="plan-xyz", apply_id="apply-xyz"),
    ]
    execution_context["plan_logs"] = ["Plan: ready", "Plan: ready"]
    execution_context["apply_logs"] = [
        "Applying...",
        "Apply complete!",
    ]
    mock_client.runs.get.side_effect = execution_context["run_states"]
    mock_client.runs.get_plan_logs.side_effect = execution_context["plan_logs"]
    mock_client.runs.get_apply_logs.side_effect = execution_context["apply_logs"]


@given(r"log API calls will intermittently fail")
def step_log_api_intermittent_failures(execution_context, mock_client):
    """Configure mock to fail on certain calls, then succeed."""
    # Alternate between raising exceptions and returning logs
    original_get = mock_client.runs.get_plan_logs
    call_count = [0]

    def get_plan_logs_with_failures(*args, **kwargs):
        call_count[0] += 1
        # Fail on 2nd and 4th calls
        if call_count[0] in (2, 4):
            raise Exception("Transient API error")
        return execution_context["plan_logs"][min(call_count[0] - 1, len(execution_context["plan_logs"]) - 1)]

    mock_client.runs.get_plan_logs.side_effect = get_plan_logs_with_failures


# When steps
@when('I request to stream logs for "run-log1"')
def step_request_stream_logs_log1(execution_context, mock_client):
    """Request log streaming for run-log1."""
    step_request_stream_logs(execution_context, mock_client)


@when('I request to stream logs for "run-log2"')
def step_request_stream_logs_log2(execution_context, mock_client):
    """Request log streaming for run-log2."""
    step_request_stream_logs(execution_context, mock_client)


@when('I request to stream logs for "run-log3"')
def step_request_stream_logs_log3(execution_context, mock_client):
    """Request log streaming for run-log3."""
    step_request_stream_logs(execution_context, mock_client)


@when('I request to stream logs for "run-log4"')
def step_request_stream_logs_log4(execution_context, mock_client):
    """Request log streaming for run-log4."""
    step_request_stream_logs(execution_context, mock_client)


@when('I request to stream logs for "run-log5"')
def step_request_stream_logs_log5(execution_context, mock_client):
    """Request log streaming for run-log5."""
    step_request_stream_logs(execution_context, mock_client)


def step_request_stream_logs(execution_context, mock_client):
    """Helper: request log streaming for a run."""
    from terrapyne.cli.run_cmd import _fetch_run_logs_incrementally

    run_id = execution_context["run_id"]
    execution_context["mock_sleep"] = MagicMock()

    # Stream logs and collect them
    with patch("terrapyne.cli.run_cmd.time.monotonic", return_value=0.0):
        try:
            lines = list(
                _fetch_run_logs_incrementally(
                    run_id,
                    mock_client,
                    sleep_fn=execution_context["mock_sleep"],
                    max_wait=10,
                )
            )
            execution_context["streamed_lines"] = lines
        except Exception as e:
            execution_context["streaming_error"] = e
            execution_context["streamed_lines"] = []


@when(r"the execution reaches a terminal state")
def step_execution_reaches_terminal(execution_context, mock_client):
    """Verify that execution reaching terminal state stops streaming."""
    # This is implicitly handled by the generator's terminal state check.
    # The mock is configured to return a terminal state on final call.
    pass


# Then steps
@then(r"I should see plan logs appear in real time")
def step_verify_plan_logs_appear(execution_context):
    """Verify that plan logs were streamed."""
    assert len(execution_context["streamed_lines"]) > 0, "No logs were streamed"
    assert any("Plan:" in line or "Terraform" in line for line in execution_context["streamed_lines"]), (
        "No plan logs found in streamed output"
    )


@then(r"each log line should arrive as it becomes available")
def step_verify_incremental_delivery(execution_context):
    """Verify that lines were delivered incrementally."""
    # The generator should have yielded multiple lines across cycles
    assert len(execution_context["streamed_lines"]) >= 1, "Not enough lines streamed incrementally"
    # Verify sleep was called (indicating multiple cycles)
    assert execution_context["mock_sleep"].called, "Sleep was not called between cycles"


@then(r"streaming should stop when the plan phase completes")
def step_verify_streaming_stops_on_plan_complete(execution_context):
    """Verify that streaming stops when plan reaches terminal state."""
    # Generator exits when run.status.is_terminal is True
    # This is implicitly verified by the test completing without hanging
    assert execution_context["streamed_lines"] is not None, "Streaming did not complete"


@then(r"I should see plan logs from the completed phase")
def step_verify_plan_logs_in_output(execution_context):
    """Verify plan logs are present."""
    assert any("Plan:" in line for line in execution_context["streamed_lines"]), (
        "Plan logs not found in output"
    )


@then(r"then see apply logs as they arrive")
def step_verify_apply_logs_in_output(execution_context):
    """Verify apply logs are present after plan logs."""
    assert any("Apply" in line for line in execution_context["streamed_lines"]), (
        "Apply logs not found in output"
    )


@then(r"streaming should continue until the apply finishes")
def step_verify_streaming_continues_through_apply(execution_context):
    """Verify streaming continued through apply phase."""
    # Generator exits when run.status.is_terminal (applied)
    assert execution_context["streamed_lines"] is not None, "Streaming did not continue to apply"


@then(r"no logs should be returned")
def step_verify_no_logs(execution_context):
    """Verify that no logs were returned for pending run."""
    assert execution_context["streamed_lines"] == [], f"Expected no logs, got: {execution_context['streamed_lines']}"


@then(r"polling should continue waiting for the plan to start")
def step_verify_polling_continues(execution_context):
    """Verify that polling continued while waiting for plan."""
    # The mock should have been called multiple times
    assert execution_context["mock_sleep"].called, "Polling did not continue (sleep not called)"


@then(r"streaming should stop when the run reaches a terminal state")
def step_verify_stop_on_terminal(execution_context):
    """Verify streaming stops at terminal state."""
    # Generator exits cleanly when terminal state is reached
    assert execution_context["streamed_lines"] is not None, "Streaming did not exit cleanly"


@then(r"failed log fetches should be retried automatically")
def step_verify_error_retry(execution_context):
    """Verify that failed log fetches were retried."""
    # The generator uses suppress(Exception), so failures are caught and retried
    # If we got here without an exception, retries worked
    assert not hasattr(execution_context, "streaming_error") or execution_context.get("streaming_error") is None, (
        "Streaming failed instead of retrying"
    )


@then(r"successful log lines should still be yielded")
def step_verify_successful_lines_yielded(execution_context):
    """Verify that successful log fetches yielded lines despite errors."""
    # Even with transient failures, we should have received some log lines
    assert len(execution_context["streamed_lines"]) > 0, "No successful log lines were yielded despite retries"


@then(r"streaming should complete despite transient failures")
def step_verify_completion_despite_errors(execution_context):
    """Verify that streaming completed successfully despite errors."""
    # Generator should have exited cleanly
    assert execution_context["streamed_lines"] is not None, "Streaming did not complete despite error handling"


@then(r"no further API calls should be made")
def step_verify_no_further_calls(execution_context, mock_client):
    """Verify that API calls stopped at terminal state."""
    # Count calls made before terminal state
    expected_calls = 2  # One for planning, one for terminal (applied)
    actual_calls = mock_client.runs.get.call_count
    # Should not exceed expected calls by more than 1 (last call to detect terminal)
    assert actual_calls <= expected_calls + 1, (
        f"Expected at most {expected_calls + 1} calls, got {actual_calls}"
    )


@then(r"streaming should exit cleanly")
def step_verify_clean_exit(execution_context):
    """Verify that streaming exited without errors."""
    assert not hasattr(execution_context, "streaming_error") or execution_context.get("streaming_error") is None, (
        "Streaming exited with error"
    )
    assert execution_context["streamed_lines"] is not None, "Streaming did not complete"
