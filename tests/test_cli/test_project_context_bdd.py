"""BDD tests for project context resolution."""
import pytest
from unittest.mock import MagicMock, patch
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.project import Project
from terrapyne.models.workspace import Workspace
from terrapyne.api.client import TFCClient

runner = CliRunner()

@pytest.fixture
def mock_api_client(request):
    p1 = patch("terrapyne.cli.project_cmd.TFCClient")
    p2 = patch("terrapyne.cli.workspace_cmd.TFCClient")
    p3 = patch("terrapyne.cli.project_cmd.validate_context")
    p4 = patch("terrapyne.cli.workspace_cmd.validate_context")
    p5 = patch("terrapyne.cli.utils.validate_context")
    
    mock_prj_client_class = p1.start()
    mock_ws_client_class = p2.start()
    mock_prj_validate = p3.start()
    mock_ws_validate = p4.start()
    mock_utils_validate = p5.start()
    
    request.addfinalizer(p1.stop)
    request.addfinalizer(p2.stop)
    request.addfinalizer(p3.stop)
    request.addfinalizer(p4.stop)
    request.addfinalizer(p5.stop)
    
    mock_instance = MagicMock(spec=TFCClient)
    mock_prj_client_class.return_value.__enter__.return_value = mock_instance
    mock_ws_client_class.return_value.__enter__.return_value = mock_instance
    
    # Mock properties
    mock_instance.workspaces = MagicMock()
    mock_instance.projects = MagicMock()
    mock_instance.runs = MagicMock()
    mock_instance.teams = MagicMock()
    
    # Default mock behavior
    mock_prj_validate.return_value = ("test-org", None)
    mock_ws_validate.return_value = ("test-org", "app-dev")
    mock_utils_validate.return_value = ("test-org", "app-dev")
    
    # Mock common attributes
    mock_instance.workspaces.get_variables.return_value = []
    mock_instance.runs.list.return_value = ([], 0)
    mock_instance.paginate_with_meta.return_value = ([], 0)
    mock_instance.paginate.return_value = []
    
    yield mock_instance

@scenario("../features/project_context.feature", "Show project details using workspace context")
def test_show_project_context():
    pass

@scenario("../features/project_context.feature", "List project teams using workspace context")
def test_list_project_teams_context():
    pass

@scenario("../features/project_context.feature", "Workspace show reports the project name")
def test_workspace_show_reports_project():
    pass

@given(parsers.parse('I am in a directory for workspace "{workspace_name}"'))
def in_workspace_directory(workspace_name: str, request):
    # We patch the resolve_workspace logic in utils.py
    p1 = patch("terrapyne.cli.utils.resolve_workspace", return_value=workspace_name)
    p2 = patch("terrapyne.cli.utils.resolve_organization", return_value="test-org")
    p1.start()
    p2.start()
    request.addfinalizer(p1.stop)
    request.addfinalizer(p2.stop)
    return workspace_name

@given(parsers.parse('workspace "{workspace_name}" belongs to project "{project_name}"'))
def workspace_belongs_to_project(mock_api_client: MagicMock, workspace_name: str, project_name: str):
    # Setup real Workspace and Project objects for rendering
    ws = Workspace(
        id=f"ws-{workspace_name}",
        name=workspace_name,
        project_id=f"prj-{project_name}",
        project_name=project_name,
    )
    prj = Project(
        id=f"prj-{project_name}",
        name=project_name,
        organization={"name": "test-org"},
    )
    
    # Mock workspaces list return value
    mock_api_client.workspaces.list.return_value = ([ws], 1)
    # Mock workspace get return value
    mock_api_client.workspaces.get.return_value = ws
    # Mock project get return value
    mock_api_client.projects.get_by_id.return_value = prj
    mock_api_client.projects.get_by_name.return_value = prj
    
    # Mock paginate for team access
    mock_api_client.paginate.return_value = [
        {
            "id": "tpa-123",
            "type": "team-project-access",
            "attributes": {"access": "admin"},
            "relationships": {
                "team": {"data": {"id": "team-123", "type": "teams"}},
                "project": {"data": {"id": prj.id, "type": "projects"}}
            }
        }
    ]
    # Mock get for team name
    mock_api_client.get.return_value = {
        "data": {
            "id": "team-123",
            "attributes": {"name": "Admins"}
        }
    }

@when(parsers.parse('I run "{command}"'), target_fixture="cli_result")
def run_command(command: str):
    args = command.replace("tfc ", "").split()
    return runner.invoke(app, args, catch_exceptions=False)

@then("the command should succeed")
def command_succeeds(cli_result):
    assert cli_result.exit_code == 0, f"Command failed with output: {cli_result.stdout}"

@then(parsers.parse('the output should show details for project "{project_name}"'))
def output_shows_project(cli_result, project_name: str):
    assert f"Project: {project_name}" in cli_result.stdout

@then(parsers.parse('the output should show team access for project "{project_name}"'))
def output_shows_team_access(cli_result, project_name: str):
    assert project_name in cli_result.stdout

@then(parsers.parse('the output should show project "{project_name}" in workspace details'))
def output_shows_project_in_workspace(cli_result, project_name: str):
    assert project_name in cli_result.stdout
    # Check for "Project" field
    assert "Project" in cli_result.stdout
