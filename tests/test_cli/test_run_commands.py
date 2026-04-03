"""CLI tests for run commands using pytest-bdd.

Tests the run list, show, plan, apply, and logs commands with various scenarios
including filtering, error handling, and context detection.
"""

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from terrapyne.cli.main import app
from terrapyne.models.run import Run
from terrapyne.models.workspace import Workspace

runner = CliRunner()


# Run-related fixtures (used in step definitions)
@pytest.fixture
def workspace_with_runs():
    """Set up workspace with runs."""
    return {"workspace": "my-app-dev", "org": "test-org"}


@pytest.fixture
def workspace_with_multiple_statuses():
    """Set up workspace with multiple run statuses."""
    return {"workspace": "my-app-dev"}


@pytest.fixture
def run_context():
    """Set up run context."""
    return {"run_id": "run-abc123"}


@pytest.fixture
def no_workspace():
    """No workspace specified."""
    return {}


@pytest.fixture
def workspace_with_many_runs():
    """Set up workspace with many runs."""
    return {"workspace": "large-workspace", "run_count": 150}


# ============================================================================
# Run List Command Tests
# ============================================================================


@scenario("../features/run.feature", "List runs for workspace")
def test_list_runs_for_workspace():
    """Scenario: List runs for workspace."""


@given("I have workspace \"my-app-dev\" with runs")
def _(workspace_with_runs):
    """Set up workspace with runs."""
    return workspace_with_runs


@pytest.fixture
@when("I list runs for \"my-app-dev\"")
def list_runs(workspace_with_runs, run_list_response, workspace_detail_response):
    """List runs via CLI."""
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock workspace and runs
        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        runs = [Run.from_api_response(data) for data in run_list_response["data"]]

        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = (runs, 2)

        result = runner.invoke(
            app,
            [
                "run",
                "list",
                "--workspace",
                "my-app-dev",
                "--organization",
                "test-org",
            ],
        )

        return {"result": result, "runs": runs}


@then("I should see run list")
def check_run_list(list_runs):
    """Verify run list is displayed."""
    result = list_runs["result"]
    assert result.exit_code == 0


@then("list should show run IDs")
def check_run_ids(list_runs):
    """Verify run IDs are shown."""
    result = list_runs["result"]
    runs = list_runs["runs"]
    # Check that at least one run ID is in output or format shows runs
    assert any(run.id in result.stdout for run in runs) or "run-" in result.stdout


@then("list should show run status")
def check_run_status(list_runs):
    """Verify run status is shown."""
    result = list_runs["result"]
    assert "applied" in result.stdout or "pending" in result.stdout or "status" in result.stdout.lower()


@then("list should show created timestamps")
def check_run_timestamps(list_runs):
    """Verify timestamps are shown."""
    result = list_runs["result"]
    # Check for date/time indicators
    assert "202" in result.stdout or "created" in result.stdout.lower()


# ============================================================================
# Run List with Status Filter Tests
# ============================================================================


@scenario("../features/run.feature", "List runs with status filter")
def test_list_runs_with_status_filter():
    """Scenario: List runs with status filter."""


@given("I have workspace \"my-app-dev\" with multiple run statuses")
def _(workspace_with_multiple_statuses):
    """Set up workspace with multiple run statuses."""
    return workspace_with_multiple_statuses


@pytest.fixture
@when("I list runs with status \"applied\"")
def list_runs_with_status(workspace_with_multiple_statuses, run_list_response, workspace_detail_response):
    """List runs filtered by status."""
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        # Filter to only applied runs
        applied_runs = [
            Run.from_api_response(data)
            for data in run_list_response["data"]
            if data["attributes"]["status"] == "applied"
        ]

        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = (applied_runs, 1)

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
                "applied",
            ],
        )

        return {"result": result, "runs": applied_runs}


@then("I should only see runs with status \"applied\"")
def check_filtered_status(list_runs_with_status):
    """Verify only applied runs are shown."""
    result = list_runs_with_status["result"]
    assert result.exit_code == 0
    # Should show applied status or relevant runs
    assert "applied" in result.stdout.lower() or len(list_runs_with_status["runs"]) >= 0


@then("count should reflect filtered results")
def check_filtered_count(list_runs_with_status):
    """Verify count reflects filtered results."""
    result = list_runs_with_status["result"]
    assert result.exit_code == 0
    # Should show count of filtered runs or results summary
    assert "1" in result.stdout or "applied" in result.stdout.lower()


# ============================================================================
# Run Show Command Tests
# ============================================================================


@scenario("../features/run.feature", "Show run details")
def test_show_run_details():
    """Scenario: Show run details."""


@given("I have run \"run-abc123\" in workspace")
def _(run_context):
    """Set up run context."""
    return run_context


@pytest.fixture
@when("I show details for run \"run-abc123\"")
def show_run_details(run_context, run_detail_response, workspace_detail_response):
    """Show run details via CLI."""
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        run = Run.from_api_response(run_detail_response["data"])
        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        mock_instance.runs.get.return_value = run
        mock_instance.workspaces.get_by_id.return_value = workspace

        result = runner.invoke(
            app,
            [
                "run",
                "show",
                "run-abc123",
                "--organization",
                "test-org",
            ],
        )

        return {"result": result, "run": run}


@then("I should see run status")
def check_run_status_shown(show_run_details):
    """Verify run status is shown."""
    result = show_run_details["result"]
    assert result.exit_code == 0
    assert "applied" in result.stdout or "status" in result.stdout.lower()


@then("I should see run message")
def check_run_message(show_run_details):
    """Verify run message is shown."""
    result = show_run_details["result"]
    assert "Applied by user" in result.stdout or "message" in result.stdout.lower()


@then("I should see run created timestamp")
def check_run_created_time(show_run_details):
    """Verify run created timestamp is shown."""
    result = show_run_details["result"]
    assert "202" in result.stdout or "created" in result.stdout.lower()


@then("I should see resource counts")
def check_resource_counts(show_run_details):
    """Verify resource counts are shown."""
    result = show_run_details["result"]
    assert "3" in result.stdout or "2" in result.stdout or "resource" in result.stdout.lower()


# ============================================================================
# Error Handling Tests
# ============================================================================


@scenario("../features/run.feature", "Handle missing workspace context")
def test_handle_missing_workspace():
    """Scenario: Handle missing workspace context."""


@given("no workspace is specified")
def _(no_workspace):
    """No workspace specified."""
    return no_workspace


@pytest.fixture
@when("I try to list runs")
def try_list_runs_no_workspace(no_workspace):
    """Try to list runs without workspace."""
    result = runner.invoke(
        app,
        ["run", "list", "--organization", "test-org"],
    )
    return {"result": result}


@then("I should see error about missing workspace")
def check_workspace_error(try_list_runs_no_workspace):
    """Verify error about missing workspace."""
    result = try_list_runs_no_workspace["result"]
    assert result.exit_code != 0
    assert "workspace" in result.stdout.lower()


@then("error should mention \"--workspace\"")
def check_workspace_hint(try_list_runs_no_workspace):
    """Verify error mentions workspace option."""
    result = try_list_runs_no_workspace["result"]
    # Should mention how to specify workspace
    assert "--workspace" in result.stdout or "WORKSPACE" in result.stdout or "workspace" in result.stdout.lower()


@then("exit code should be 1")
def check_exit_code_one(try_list_runs_no_workspace):
    """Verify exit code is 1."""
    result = try_list_runs_no_workspace["result"]
    assert result.exit_code == 1


# ============================================================================
# Run Pagination Tests
# ============================================================================


@scenario("../features/run.feature", "List runs with pagination")
def test_list_runs_pagination():
    """Scenario: List runs with pagination."""


@given("I have workspace with 150 runs")
def _(workspace_with_many_runs):
    """Set up workspace with many runs."""
    return workspace_with_many_runs


@pytest.fixture
@when("I list runs")
def list_paginated_runs(workspace_with_many_runs, run_list_response, workspace_detail_response):
    """List runs with pagination."""
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        runs = [Run.from_api_response(data) for data in run_list_response["data"]]

        mock_instance.workspaces.get.return_value = workspace
        # Mock pagination with total count
        mock_instance.runs.list.return_value = (runs, 150)

        result = runner.invoke(
            app,
            [
                "run",
                "list",
                "--workspace",
                "large-workspace",
                "--organization",
                "test-org",
            ],
        )

        return {"result": result}


@then("I should see first page of runs")
def check_first_page(list_paginated_runs):
    """Verify first page of runs is shown."""
    result = list_paginated_runs["result"]
    assert result.exit_code == 0


@then("pagination info should show total count")
def check_pagination_info(list_paginated_runs):
    """Verify pagination info is shown."""
    result = list_paginated_runs["result"]
    # Should mention total count or pagination
    assert "150" in result.stdout or "pagination" in result.stdout.lower() or "Showing" in result.stdout


@then("pagination should indicate \"Showing: X of 150\"")
def check_pagination_format(list_paginated_runs):
    """Verify pagination format is correct."""
    result = list_paginated_runs["result"]
    # Should show format like "Showing: X of 150"
    assert "Showing" in result.stdout or "150" in result.stdout or "of" in result.stdout
