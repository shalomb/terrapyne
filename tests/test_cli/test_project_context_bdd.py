"""BDD tests for project context resolution."""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.project import Project
from terrapyne.models.workspace import Workspace

runner = CliRunner()


@scenario("../features/project_context.feature", "Show project details using workspace context")
def test_project_show_from_context():
    """Scenario: Show project details using workspace context."""


@scenario("../features/project_context.feature", "List project teams using workspace context")
def test_project_teams_from_context():
    """Scenario: List project teams using workspace context."""


@scenario("../features/project_context.feature", "Workspace show reports the project name")
def test_workspace_show_reports_project():
    """Scenario: Workspace show reports the project name."""


# ============================================================================
# Background / Given Steps
# ============================================================================


@given('I am in a directory for workspace "app-dev"')
def local_linked_to_workspace():
    """Mock local workspace linkage."""
    pass


@given('workspace "app-dev" belongs to project "Project-X"')
def workspace_belongs_to_project():
    """Mock workspace-project relationship."""
    pass


# ============================================================================
# When Steps
# ============================================================================


@pytest.fixture
@when('I run "tfc project show"', target_fixture="cli_result")
def request_project_details_no_name():
    """Request project details via CLI without arguments."""
    with (
        patch("terrapyne.cli.project_cmd.validate_context") as mock_validate_cmd,
        patch("terrapyne.cli.utils.validate_context") as mock_validate_utils,
        patch("terrapyne.cli.project_cmd.TFCClient") as mock_client,
    ):
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        project = Project.model_construct(id="prj-123", name="Project-X")
        # In show_project, org, _ = validate_context(organization) is called
        mock_validate_cmd.return_value = ("test-org", None)
        # In resolve_project_context, validate_context(organization, require_workspace=True) is called
        mock_validate_utils.return_value = ("test-org", "app-dev")

        mock_instance.workspaces.list.return_value = (iter([]), 0)
        mock_instance.projects.get_by_id.return_value = project

        # Mock workspace get as it's used to resolve project from workspace
        ws = Workspace.model_construct(id="ws-abc", name="app-dev", project_id="prj-123")
        mock_instance.workspaces.get.return_value = ws

        result = runner.invoke(app, ["project", "show"])
        return {"result": result, "project": project}


@pytest.fixture
@when('I run "tfc project teams"', target_fixture="cli_result")
def request_project_teams_no_name():
    """Request project teams via CLI without arguments."""
    with (
        patch("terrapyne.cli.project_cmd.validate_context") as mock_validate_cmd,
        patch("terrapyne.cli.utils.validate_context") as mock_validate_utils,
        patch("terrapyne.cli.project_cmd.TFCClient") as mock_client,
    ):
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        project = Project.model_construct(id="prj-123", name="Project-X")
        mock_validate_cmd.return_value = ("test-org", None)
        mock_validate_utils.return_value = ("test-org", "app-dev")

        # Mock workspace and project resolution
        ws = Workspace.model_construct(id="ws-abc", name="app-dev", project_id="prj-123")
        mock_instance.workspaces.get.return_value = ws
        mock_instance.projects.get_by_id.return_value = project
        mock_instance.projects.list_team_access.return_value = []

        result = runner.invoke(app, ["project", "teams"])
        return {"result": result, "project": project}


@pytest.fixture
@when('I run "tfc workspace show"', target_fixture="cli_result")
def request_workspace_details():
    """Request workspace details via CLI."""
    with (
        patch("terrapyne.cli.workspace_cmd.validate_context") as mock_validate,
        patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client,
    ):
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock workspace resolution
        ws = Workspace.model_construct(
            id="ws-abc", name="app-dev", project_id="prj-123", tag_names=[]
        )
        mock_validate.return_value = ("test-org", "app-dev")
        mock_instance.workspaces.get.return_value = ws
        mock_instance.runs.list.return_value = ([], 0)
        mock_instance.workspaces.get_variables.return_value = []

        result = runner.invoke(app, ["workspace", "show"])
        return {"result": result, "workspace": ws}


# ============================================================================
# Then Steps
# ============================================================================


@then("the command should succeed")
def command_succeeds(cli_result):
    """Verify command success."""
    result = cli_result["result"]
    assert result.exit_code == 0, f"Command failed with output: {result.stdout}"


@then(parsers.parse('the output should show details for project "{project}"'))
def check_project_details(cli_result, project):
    """Verify project details are shown."""
    result = cli_result["result"]
    assert project in result.stdout


@then(parsers.parse('the output should show team access for project "{project}"'))
def check_project_teams(cli_result, project):
    """Verify project teams are shown."""
    result = cli_result["result"]
    assert project in result.stdout


@then(parsers.parse('the output should show project "{project}" in workspace details'))
def check_parent_project(cli_result, project):
    """Verify parent project is identified."""
    result = cli_result["result"]
    # Our mock setup uses prj-123 for the ID
    assert "prj-123" in result.stdout or project in result.stdout
