"""BDD tests for project context resolution."""
import pytest
from unittest.mock import MagicMock, patch
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.project import Project
from terrapyne.models.workspace import Workspace

runner = CliRunner()

@pytest.fixture
def mock_api_client():
    from unittest.mock import PropertyMock
    
    with patch("terrapyne.cli.project_cmd.TFCClient") as mock_prj_client_class, \
         patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_ws_client_class, \
         patch("terrapyne.cli.project_cmd.validate_context") as mock_prj_validate, \
         patch("terrapyne.cli.workspace_cmd.validate_context") as mock_ws_validate:
        
        mock_instance = MagicMock()
        mock_prj_client_class.return_value.__enter__.return_value = mock_instance
        mock_ws_client_class.return_value.__enter__.return_value = mock_instance
        
        # Mock organization resolution
        mock_prj_validate.return_value = ("test-org", None)
        mock_ws_validate.return_value = ("test-org", "app-dev")
        
        # Mock common attributes
        mock_workspaces = MagicMock()
        mock_projects = MagicMock()
        type(mock_instance).workspaces = PropertyMock(return_value=mock_workspaces)
        type(mock_instance).projects = PropertyMock(return_value=mock_projects)
        
        mock_workspaces.get_variables.return_value = []
        mock_instance.paginate_with_meta.return_value = (iter([]), 0)
        mock_instance.paginate.return_value = iter([])
        
        yield mock_instance

@scenario("../features/project_context.feature", "Show project details using workspace context")
def test_show_project_context() -> None:
    pass

@scenario("../features/project_context.feature", "List project teams using workspace context")
def test_list_project_teams_context() -> None:
    pass

@scenario("../features/project_context.feature", "Workspace show reports the project name")
def test_workspace_show_reports_project() -> None:
    pass

@given(parsers.parse('I am in a directory for workspace "{workspace_name}"'))
def in_workspace_directory(workspace_name: str):
    # We patch the resolve_workspace logic in utils.py
    with patch("terrapyne.cli.utils.resolve_workspace", return_value=workspace_name), \
         patch("terrapyne.cli.utils.resolve_organization", return_value="test-org"):
        yield

@given(parsers.parse('workspace "{workspace_name}" belongs to project "{project_name}"'))
def workspace_belongs_to_project(mock_api_client: MagicMock, workspace_name: str, project_name: str):
    # Setup real Workspace and Project objects for rendering
    ws = Workspace(
        id=f"ws-{workspace_name}",
        name=workspace_name,
        project_id=f"prj-{project_name}",
        project_name=project_name
    )
    proj = Project(
        id=f"prj-{project_name}",
        name=project_name,
        description=f"Project {project_name}",
        created_at="2025-03-13T00:00:00Z"
    )
    
    # Mock workspaces.get
    mock_api_client.workspaces.get.return_value = ws
    
    # Mock projects methods
    mock_api_client.projects.get_by_name.return_value = proj
    mock_api_client.projects.get_by_id.return_value = proj

    # Setup mock responses based on path
    def mock_get(path, **kwargs):
        if "workspaces" in path:
            return {
                "data": {
                    "id": f"ws-{workspace_name}",
                    "type": "workspaces",
                    "attributes": {
                        "name": workspace_name,
                    },
                    "relationships": {
                        "project": {
                            "data": {"id": f"prj-{project_name}", "type": "projects"}
                        }
                    }
                },
                "included": [
                    {
                        "id": f"prj-{project_name}",
                        "type": "projects",
                        "attributes": {
                            "name": project_name
                        }
                    }
                ]
            }
        elif "projects" in path:
            return {
                "data": {
                    "id": f"prj-{project_name}",
                    "type": "projects",
                    "attributes": {
                        "name": project_name,
                    }
                }
            }
        elif "teams" in path:
            return {"data": {"id": "team-1", "attributes": {"name": "Devs"}}}
        return {}

    mock_api_client.get.side_effect = mock_get
    
    # Mock team access pagination
    def mock_paginate(path, **kwargs):
        if "team-projects" in path or "team-access" in path:
            return iter([
                {
                    "id": "tpa-1",
                    "type": "team-project-access",
                    "attributes": {
                        "access": "admin"
                    },
                    "relationships": {
                        "team": {
                            "data": {"id": "team-1", "type": "teams"}
                        }
                    }
                }
            ])
        elif "workspaces" in path:
            return iter([
                {
                    "id": f"ws-{workspace_name}",
                    "type": "workspaces",
                    "attributes": {"name": workspace_name}
                }
            ])
        return iter([])

    mock_api_client.paginate.side_effect = mock_paginate
    
    # Mock paginate_with_meta just in case
    def mock_paginate_meta(path, **kwargs):
        items = list(mock_paginate(path, **kwargs))
        return iter(items), len(items)
    
    mock_api_client.paginate_with_meta.side_effect = mock_paginate_meta
    
    # Mock workspaces list return value
    mock_api_client.workspaces.list.return_value = (iter([ws]), 1)
    
    # Mock team access (for teams command)
    from terrapyne.models.team_access import TeamProjectAccess
    team_acc = TeamProjectAccess(
        id="tpa-1",
        project_id=f"prj-{project_name}",
        team_id="team-1",
        team_name="Devs",
        access="admin"
    )
    mock_api_client.projects.list_team_access.return_value = [team_acc]

@when(parsers.parse('I run "{command}"'), target_fixture="cli_result")
def run_command(command: str):
    args = command.replace("tfc ", "").split()
    return runner.invoke(app, args, catch_exceptions=False)

@then("the command should succeed")
def command_succeeds(cli_result):
    assert cli_result.exit_code == 0, f"Command failed with output: {cli_result.stdout}"

@then(parsers.parse('the output should show details for project "{project_name}"'))
def output_shows_project_details(cli_result, project_name: str):
    assert project_name in cli_result.stdout

@then(parsers.parse('the output should show team access for project "{project_name}"'))
def output_shows_team_access(cli_result, project_name: str):
    assert project_name in cli_result.stdout

@then(parsers.parse('the output should show project "{project_name}" in workspace details'))
def output_shows_project_in_workspace(cli_result, project_name: str):
    assert project_name in cli_result.stdout
    # Check for "Project" field
    assert "Project" in cli_result.stdout
