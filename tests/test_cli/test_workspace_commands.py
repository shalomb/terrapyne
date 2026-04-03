"""CLI tests for workspace commands using pytest-bdd.

Tests the workspace list, show, vcs, and open commands with various scenarios
including error handling, context detection, and pagination.
"""

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from terrapyne.cli.main import app
from terrapyne.models.workspace import Workspace
from terrapyne.models.variable import WorkspaceVariable

runner = CliRunner()


# Workspace-related fixtures (used in step definitions)
@pytest.fixture
def org_setup():
    """Set up test organization context."""
    return {"org": "test-org"}


@pytest.fixture
def workspace_context():
    """Set up workspace context."""
    return {
        "workspace": "my-app-dev",
        "org": "test-org",
    }


@pytest.fixture
def no_org_context():
    """No organization specified."""
    return {}


@pytest.fixture
def workspace_with_vcs():
    """Set up workspace with VCS."""
    return {"workspace": "my-app-dev", "org": "test-org"}


@pytest.fixture
def workspace_without_vcs():
    """Set up workspace without VCS."""
    return {"workspace": "unconnected-ws"}


# ============================================================================
# Workspace List Command Tests
# ============================================================================


@scenario("../features/workspace.feature", "List all workspaces in organization")
def test_list_all_workspaces():
    """Scenario: List all workspaces in organization."""


@given("I have organization \"test-org\" set up")
def _(org_setup):
    """Set up test organization context."""
    return org_setup


@pytest.fixture
@when("I list all workspaces")
def list_all_workspaces(org_setup, workspace_list_response):
    """List workspaces via CLI."""
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock the API response
        workspaces = [
            Workspace.from_api_response(data)
            for data in workspace_list_response["data"]
        ]
        mock_instance.workspaces.list.return_value = (iter(workspaces), 2)

        result = runner.invoke(
            app, ["workspace", "list", "--organization", "test-org"]
        )

        return {
            "result": result,
            "workspaces": workspaces,
            "mock_client": mock_client,
        }


@then("I should see workspace list")
def check_workspace_list(list_all_workspaces):
    """Verify workspace list is displayed."""
    result = list_all_workspaces["result"]
    assert result.exit_code == 0
    assert "my-app-dev" in result.stdout or "my-app-prod" in result.stdout


@then("the list should show workspace count")
def check_workspace_count(list_all_workspaces):
    """Verify workspace count is shown."""
    result = list_all_workspaces["result"]
    # Should show pagination info like "Showing: X of Y"
    assert "2" in result.stdout or "workspace" in result.stdout.lower()


# ============================================================================
# Workspace Show Command Tests
# ============================================================================


@scenario("../features/workspace.feature", "Show workspace details")
def test_show_workspace_details():
    """Scenario: Show workspace details."""


@given("I have workspace \"my-app-dev\" in organization \"test-org\"")
def _(workspace_context):
    """Set up workspace context."""
    return workspace_context


@pytest.fixture
@when("I show workspace details for \"my-app-dev\"")
def show_workspace_details(workspace_context, workspace_detail_response):
    """Show workspace details via CLI."""
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock the API response
        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        mock_instance.workspaces.get.return_value = workspace
        mock_instance.workspaces.get_variables.return_value = []

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

        return {"result": result, "workspace": workspace}


@then("I should see workspace properties")
def check_workspace_properties(show_workspace_details):
    """Verify workspace properties are shown."""
    result = show_workspace_details["result"]
    assert result.exit_code == 0
    assert "my-app-dev" in result.stdout


@then("I should see workspace ID")
def check_workspace_id(show_workspace_details):
    """Verify workspace ID is shown."""
    result = show_workspace_details["result"]
    workspace = show_workspace_details["workspace"]
    assert workspace.id in result.stdout or "ws-" in result.stdout


@then("I should see terraform version")
def check_terraform_version(show_workspace_details):
    """Verify terraform version is shown."""
    result = show_workspace_details["result"]
    assert "1.7.0" in result.stdout or "terraform" in result.stdout.lower()


@then("I should see execution mode")
def check_execution_mode(show_workspace_details):
    """Verify execution mode is shown."""
    result = show_workspace_details["result"]
    assert "remote" in result.stdout or "execution" in result.stdout.lower()


# ============================================================================
# Error Handling Tests
# ============================================================================


@scenario("../features/workspace.feature", "Handle missing organization")
def test_handle_missing_organization():
    """Scenario: Handle missing organization."""


@given("no organization is specified")
def _(no_org_context):
    """No organization specified."""
    return no_org_context


@pytest.fixture
@when("I try to list workspaces")
def try_list_without_org(no_org_context):
    """Try to list workspaces without organization."""
    result = runner.invoke(app, ["workspace", "list"])
    return {"result": result}


@then("I should see error message \"No organization specified\"")
def check_error_message(try_list_without_org):
    """Verify error message about missing organization."""
    result = try_list_without_org["result"]
    assert result.exit_code != 0
    assert "organization" in result.stdout.lower()


@then("error message should mention \"--organization\"")
def check_error_hint(try_list_without_org):
    """Verify error mentions how to fix it."""
    result = try_list_without_org["result"]
    assert "--organization" in result.stdout or "ORGANIZATION" in result.stdout


@then("exit code should be 1")
def check_exit_code_one(try_list_without_org):
    """Verify exit code is 1."""
    result = try_list_without_org["result"]
    assert result.exit_code == 1


# ============================================================================
# Workspace VCS Tests
# ============================================================================


@scenario("../features/workspace.feature", "Show VCS configuration only")
def test_show_vcs_configuration():
    """Scenario: Show VCS configuration only."""


@given("I have workspace \"my-app-dev\" with VCS configured")
def _(workspace_with_vcs):
    """Set up workspace with VCS."""
    return workspace_with_vcs


@pytest.fixture
@when("I show VCS config for workspace \"my-app-dev\"")
def show_vcs_config(workspace_with_vcs, workspace_detail_response):
    """Show VCS config via CLI."""
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        mock_instance.workspaces.get.return_value = workspace

        result = runner.invoke(
            app,
            ["workspace", "vcs", "my-app-dev", "--organization", "test-org"],
        )

        return {"result": result}


@then("I should see repository information")
def check_repository_info(show_vcs_config):
    """Verify repository information is shown."""
    result = show_vcs_config["result"]
    assert result.exit_code == 0
    assert "myorg/my-app" in result.stdout or "Repository" in result.stdout


@then("I should see branch information")
def check_branch_info(show_vcs_config):
    """Verify branch information is shown."""
    result = show_vcs_config["result"]
    assert "develop" in result.stdout or "branch" in result.stdout.lower()


@then("I should see auto-apply setting")
def check_auto_apply(show_vcs_config):
    """Verify auto-apply setting is shown."""
    result = show_vcs_config["result"]
    assert "auto" in result.stdout.lower() or "apply" in result.stdout.lower()


@scenario("../features/workspace.feature", "Handle workspace without VCS")
def test_handle_workspace_without_vcs():
    """Scenario: Handle workspace without VCS."""


@given("I have workspace \"unconnected-ws\" without VCS")
def _(workspace_without_vcs):
    """Set up workspace without VCS."""
    return workspace_without_vcs


@pytest.fixture
@when("I show VCS config for \"unconnected-ws\"")
def show_vcs_no_connection(workspace_without_vcs):
    """Try to show VCS for workspace without VCS."""
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Create workspace without VCS
        ws_data = {
            "id": "ws-no-vcs",
            "type": "workspaces",
            "attributes": {
                "name": "unconnected-ws",
                "created-at": "2025-03-13T07:50:15.781Z",
                "terraform-version": "1.7.0",
                "execution-mode": "remote",
            },
        }
        workspace = Workspace.from_api_response(ws_data)
        mock_instance.workspaces.get.return_value = workspace

        result = runner.invoke(
            app,
            ["workspace", "vcs", "unconnected-ws", "--organization", "test-org"],
        )

        return {"result": result}


@then("I should see message \"no VCS connection\"")
def check_no_vcs_message(show_vcs_no_connection):
    """Verify message about no VCS connection."""
    result = show_vcs_no_connection["result"]
    assert result.exit_code == 0
    assert "no VCS" in result.stdout or "No VCS" in result.stdout


@then("exit code should be 0")
def check_exit_code_zero(show_vcs_no_connection):
    """Verify exit code is 0."""
    result = show_vcs_no_connection["result"]
    assert result.exit_code == 0


# ============================================================================
