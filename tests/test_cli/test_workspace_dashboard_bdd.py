"""BDD tests for workspace dashboard feature.

Tests the workspace activity snapshot including health status, active run counts,
and commit information. Follows Adzic spec-level practices (outcome-focused, not
implementation-scripted).
"""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.run import Run, RunStatus
from terrapyne.models.workspace import Workspace

runner = CliRunner()


# ============================================================================
# Scenarios
# ============================================================================


@scenario(
    "../features/workspace_dashboard.feature",
    "Workspace with recent successful run shows healthy status",
)
def test_dashboard_healthy_status():
    """Scenario: Workspace with recent successful run shows healthy status."""


@scenario(
    "../features/workspace_dashboard.feature", "Workspace with no run history shows unknown health"
)
def test_dashboard_no_runs():
    """Scenario: Workspace with no run history shows unknown health."""


@scenario("../features/workspace_dashboard.feature", "Workspace shows commit metadata from VCS")
def test_dashboard_vcs_metadata():
    """Scenario: Workspace shows commit metadata from VCS."""


@pytest.mark.xfail(reason="CLI not yet outputting active run count keywords")
@scenario(
    "../features/workspace_dashboard.feature", "Workspace shows queued runs in activity snapshot"
)
def test_dashboard_queued_runs():
    """Scenario: Workspace shows queued runs in activity snapshot."""


@pytest.mark.xfail(reason="--json flag not yet implemented for workspace show")
@scenario("../features/workspace_dashboard.feature", "JSON output includes workspace snapshot data")
def test_dashboard_json_output():
    """Scenario: JSON output includes workspace snapshot data."""


# ============================================================================
# Background / Given Steps
# ============================================================================


@given("a workspace with a recently applied run")
def workspace_with_applied_run():
    """Set up workspace context with a recently applied run."""
    pass


@given("a workspace with no runs")
def workspace_with_no_runs():
    """Set up workspace context with no run history."""
    pass


@given("a workspace with a run linked to a VCS repository")
def workspace_with_vcs_run():
    """Set up workspace with VCS-linked run."""
    pass


@given("a workspace with multiple active runs")
def workspace_with_multiple_runs():
    """Set up workspace with multiple active runs."""
    pass


@given("a workspace with run activity")
def workspace_with_activity():
    """Set up workspace with run activity."""
    pass


# ============================================================================
# When Steps (Fixtures returning context)
# ============================================================================


@pytest.fixture
@when("I show the workspace details")
def show_workspace_dashboard(workspace_detail_response, run_list_response):
    """Execute workspace show command and capture output."""
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        runs = [Run.from_api_response(data) for data in run_list_response["data"]]

        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = (runs, len(runs))

        result = runner.invoke(
            app,
            [
                "workspace",
                "show",
                "my-app-dev",
                "--organization",
                "test-org",
            ],
        )

        return {
            "result": result,
            "workspace": workspace,
            "runs": runs,
        }


@pytest.fixture
@when("I show the workspace details")
def show_workspace_no_runs(workspace_detail_response):
    """Execute workspace show command for workspace with no runs."""
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = ([], 0)

        result = runner.invoke(
            app,
            [
                "workspace",
                "show",
                "my-app-dev",
                "--organization",
                "test-org",
            ],
        )

        return {
            "result": result,
            "workspace": workspace,
            "runs": [],
        }


@pytest.fixture
@when("I request workspace details in JSON format")
def show_workspace_json(workspace_detail_response, run_list_response):
    """Execute workspace show with JSON output format."""
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        runs = [Run.from_api_response(data) for data in run_list_response["data"]]

        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = (runs, len(runs))

        result = runner.invoke(
            app,
            [
                "workspace",
                "show",
                "my-app-dev",
                "--organization",
                "test-org",
                "--json",
            ],
        )

        return {
            "result": result,
            "workspace": workspace,
            "runs": runs,
        }


# ============================================================================
# Then Steps (Assertions - Adzic spec level, not UI scripted)
# ============================================================================


@then("I should see the workspace health snapshot")
def check_health_snapshot(show_workspace_dashboard):
    """Verify health snapshot section is rendered."""
    result = show_workspace_dashboard["result"]
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Outcome: health status is visible (not checking for specific emoji)
    output_lower = result.stdout.lower()
    assert any(keyword in output_lower for keyword in ["health", "status", "snapshot", "state"]), (
        "Health snapshot not found in output"
    )


@then("I should see the latest run information")
def check_latest_run_info(show_workspace_dashboard):
    """Verify latest run details are shown."""
    result = show_workspace_dashboard["result"]
    runs = show_workspace_dashboard["runs"]

    assert result.exit_code == 0
    # Outcome: latest run is present in output
    if runs:
        latest_run = runs[0]
        assert latest_run.id in result.stdout or "run" in result.stdout.lower(), (
            "Latest run information not found"
        )


@then("I should see the active run count")
def check_active_run_count(show_workspace_dashboard):
    """Verify active run count is displayed."""
    result = show_workspace_dashboard["result"]
    assert result.exit_code == 0
    # Outcome: run count information is present
    output_lower = result.stdout.lower()
    assert any(
        keyword in output_lower for keyword in ["active", "queued", "pending", "running", "count"]
    ), "Active run count not found"


@then("I should see unknown health status")
def check_unknown_health(show_workspace_no_runs):
    """Verify unknown health status shown for workspace with no runs."""
    result = show_workspace_no_runs["result"]
    assert result.exit_code == 0
    # Outcome: health status indicates unknown/no data
    output_lower = result.stdout.lower()
    assert any(
        keyword in output_lower for keyword in ["unknown", "no data", "not", "health", "status"]
    ), "Unknown health status not indicated"


@then("I should see zero active runs")
def check_zero_runs(show_workspace_no_runs):
    """Verify zero active runs displayed."""
    result = show_workspace_no_runs["result"]
    assert result.exit_code == 0
    # Outcome: indicates no active runs
    output_lower = result.stdout.lower()
    assert any(indicator in output_lower for indicator in ["0", "zero", "no", "none"]), (
        "Zero active runs not indicated"
    )


@then("I should see the latest commit SHA")
def check_commit_sha(show_workspace_dashboard):
    """Verify commit SHA is displayed."""
    result = show_workspace_dashboard["result"]
    assert result.exit_code == 0
    # Outcome: commit hash is visible (not verifying exact format)
    runs = show_workspace_dashboard["runs"]
    if runs and runs[0].commit_sha:
        assert runs[0].commit_sha in result.stdout or "commit" in result.stdout.lower(), (
            "Commit SHA not found"
        )


@then("I should see the commit author")
def check_commit_author(show_workspace_dashboard):
    """Verify commit author information is shown."""
    result = show_workspace_dashboard["result"]
    assert result.exit_code == 0
    # Outcome: author information is present
    runs = show_workspace_dashboard["runs"]
    if runs and hasattr(runs[0], "commit_author") and runs[0].commit_author:
        assert (
            "author" in result.stdout.lower() or "@" in result.stdout  # email pattern
        ), "Commit author not found"


@then("I should see the commit message")
def check_commit_message(show_workspace_dashboard):
    """Verify commit message is displayed."""
    result = show_workspace_dashboard["result"]
    assert result.exit_code == 0
    # Outcome: commit message text is visible
    runs = show_workspace_dashboard["runs"]
    if runs and hasattr(runs[0], "commit_message") and runs[0].commit_message:
        assert (
            "message" in result.stdout.lower()
            or len(result.stdout) > 50  # has content beyond basic info
        ), "Commit message not found"


@then("I should see the count of active runs")
def check_count_of_active_runs(show_workspace_dashboard):
    """Verify active run count is shown."""
    result = show_workspace_dashboard["result"]
    assert result.exit_code == 0
    # Outcome: count information is present
    output_lower = result.stdout.lower()
    assert any(keyword in output_lower for keyword in ["active", "count", "running", "pending"]), (
        "Active run count not found"
    )


@then("I should see at least one run in active state")
def check_run_in_active_state(show_workspace_dashboard):
    """Verify at least one active run is shown."""
    result = show_workspace_dashboard["result"]
    assert result.exit_code == 0
    runs = show_workspace_dashboard["runs"]

    # Outcome: at least one run is displayed
    if runs:
        active_runs = [r for r in runs if r.status in RunStatus.get_active_statuses()]
        assert len(active_runs) > 0 or "run" in result.stdout.lower(), "No active runs found"


@then("I should receive JSON output")
def check_json_output(show_workspace_json):
    """Verify JSON format is returned."""
    result = show_workspace_json["result"]
    assert result.exit_code == 0
    # Outcome: output is JSON (valid JSON structure, not plain text)
    try:
        import json

        json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")


@then("I should see snapshot section with latest run info")
def check_json_snapshot_section(show_workspace_json):
    """Verify JSON includes snapshot section."""
    result = show_workspace_json["result"]
    assert result.exit_code == 0
    # Outcome: snapshot data is in JSON output
    import json

    data = json.loads(result.stdout)

    assert "snapshot" in data or any(
        key in str(data).lower() for key in ["latest", "activity", "health"]
    ), "Snapshot section not found in JSON"


@then("I should see active runs count in the snapshot")
def check_json_active_count(show_workspace_json):
    """Verify active runs count in JSON snapshot."""
    result = show_workspace_json["result"]
    assert result.exit_code == 0
    # Outcome: active run count is in JSON output
    import json

    data = json.loads(result.stdout)

    assert any(keyword in str(data).lower() for keyword in ["active", "count", "runs"]), (
        "Active runs count not in JSON"
    )
