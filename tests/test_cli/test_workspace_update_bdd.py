"""BDD step definitions for workspace update."""

from unittest.mock import Mock, patch

from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.workspace import Workspace

scenarios("../features/workspace_update.feature")

runner = CliRunner()


@given("the TFC API accepts workspace updates", target_fixture="mock_client")
def mock_api_accepts_update():
    """Setup mock to accept workspace updates."""
    mock_tfc_client = Mock()
    mock_workspace = Mock(spec=Workspace)
    mock_workspace.id = "ws-1234"
    mock_workspace.name = "my-app-dev"
    mock_workspace.terraform_version = "1.4.0"
    mock_workspace.execution_mode = "local"

    mock_tfc_client.workspaces.update.return_value = mock_workspace
    return mock_tfc_client


@given("the TFC API rejects the project lookup", target_fixture="mock_client")
def mock_api_rejects_project():
    """Setup mock to fail project lookup."""
    from terrapyne.core.exceptions import TFCNotFoundError

    mock_tfc_client = Mock()
    mock_tfc_client.projects.get_by_name.side_effect = TFCNotFoundError("Project not found")
    return mock_tfc_client


@when(
    'I request to update the workspace "my-app-dev" with version "1.4.0" and execution mode "local"',
    target_fixture="cli_result",
)
def req_update_workspace(mock_client):
    """Execute update workspace command."""
    with (
        patch("terrapyne.api.client.TFCClient") as c,
        patch("terrapyne.cli.context_helpers.validate_context") as v,
    ):
        v.return_value = ("test-org", None)
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(
            app,
            [
                "workspace",
                "update",
                "my-app-dev",
                "--tf-version",
                "1.4.0",
                "--execution-mode",
                "local",
                "-o",
                "test-org",
            ],
        )


@when(
    'I request to update the workspace "my-app-dev" to project "nonexistent-project"',
    target_fixture="cli_result",
)
def req_update_workspace_invalid_project(mock_client):
    """Execute update workspace command with invalid project."""
    with (
        patch("terrapyne.api.client.TFCClient") as c,
        patch("terrapyne.cli.context_helpers.validate_context") as v,
    ):
        v.return_value = ("test-org", None)
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(
            app,
            [
                "workspace",
                "update",
                "my-app-dev",
                "--project-name",
                "nonexistent-project",
                "-o",
                "test-org",
            ],
        )


@then("the command succeeds")
def command_succeeds(cli_result):
    """Verify command success."""
    assert cli_result.exit_code == 0, f"Exit code {cli_result.exit_code}: {cli_result.output}"


@then("the output shows the workspace was successfully updated")
def check_update_output(cli_result):
    """Verify update output."""
    assert "Successfully updated workspace 'my-app-dev'" in cli_result.output


@then("the command fails")
def command_fails(cli_result):
    """Verify command failure."""
    assert cli_result.exit_code != 0


@then("the error output indicates the project could not be found")
def check_project_not_found(cli_result):
    """Verify project not found error message."""
    assert "Project not found" in cli_result.output
