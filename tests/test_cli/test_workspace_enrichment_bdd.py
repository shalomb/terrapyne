"""BDD tests for workspace dashboard enrichment."""
from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.workspace import Workspace, WorkspaceVCS
from terrapyne.models.run import Run, RunStatus

runner = CliRunner()

@pytest.fixture
def mock_api_client():
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client_class, \
         patch("terrapyne.cli.workspace_cmd.validate_context") as mock_validate:
        
        mock_instance = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_instance
        
        # Test state
        test_state = {"latest_run": None, "active_count": 0}
        mock_instance._test_state = test_state

        def mock_runs_list(workspace_id=None, **kwargs):
            state = mock_instance._test_state
            latest_run = state["latest_run"]
            active_count = state["active_count"]

            # Handle consolidated call
            if kwargs.get("limit") == 20:
                runs = []
                if latest_run:
                    runs.append(latest_run)
                
                # Add dummy active runs if needed
                for i in range(active_count):
                    runs.append(Run(
                        id=f"run-active-{i}",
                        status=RunStatus.PLANNING,
                    ))
                return (runs, len(runs))
            
            # Handle fallback count call
            if kwargs.get("status"):
                return ([], active_count)
                
            return ([], 0)

        mock_instance.runs.list.side_effect = mock_runs_list
        
        # Mock organization resolution
        mock_validate.return_value = ("test-org", "app-prod")
        
        # Default mock returns
        mock_instance.workspaces.get_variables.return_value = []
        
        yield mock_instance

@scenario("../features/workspace_enrichment.feature", "Show workspace dashboard with active runs and VCS info")
def test_workspace_dashboard_snapshot() -> None:
    pass

@given(parsers.parse('a Terraform Cloud workspace "{workspace_name}" exists in project "{project_name}"'))
def workspace_exists_in_project(mock_api_client: MagicMock, workspace_name: str, project_name: str):
    ws = Workspace.model_construct(
        id=f"ws-{workspace_name}",
        name=workspace_name,
        project_id=f"prj-{project_name}",
        project_name=project_name,
        vcs_repo=WorkspaceVCS.model_construct(identifier="org/repo", branch="main"),
        terraform_version="N/A",
        working_directory="/",
        execution_mode="remote",
        auto_apply=False,
        locked=False,
        created_at=datetime.now()
    )
    mock_api_client.workspaces.get.return_value = ws
    mock_api_client.workspaces.get.side_effect = None

@given(parsers.parse('the workspace "{workspace_name}" has {count:d} runs currently queued or in progress'))
def workspace_has_queued_runs(mock_api_client: MagicMock, workspace_name: str, count: int):
    mock_api_client._test_state["active_count"] = count

@given(parsers.parse('the latest run for "{workspace_name}" was "{status}" successfully'))
def latest_run_status(mock_api_client: MagicMock, workspace_name: str, status: str):
    run = Run.model_construct(
        id="run-123",
        status=RunStatus(status),
        commit_sha="a1b2c3d",
        commit_author="Alice",
        commit_message="feat: initial commit"
    )
    mock_api_client._test_state["latest_run"] = run

@given(parsers.parse('the workspace "{workspace_name}" is linked to "{repo}" branch "{branch}"'))
def workspace_vcs_link(mock_api_client: MagicMock, workspace_name: str, repo: str, branch: str):
    # Handled in workspace_exists_in_project
    pass

@given(parsers.parse('the latest commit was "{sha}" by "{author}" - "{message}"'))
def latest_commit_info(sha: str, author: str, message: str):
    # Handled in latest_run_status
    pass

@when(parsers.parse('I run "{command}"'), target_fixture="cli_result")
def run_command(command: str):
    args = command.replace("tfc ", "").split()
    return runner.invoke(app, args, catch_exceptions=False)

@then("the command should succeed")
def command_succeeds(cli_result):
    assert cli_result.exit_code == 0, f"Command failed with output: {cli_result.stdout}"

@then(parsers.parse('the output should show "{text}"'))
def output_shows_text(cli_result, text: str):
    assert text in cli_result.stdout
