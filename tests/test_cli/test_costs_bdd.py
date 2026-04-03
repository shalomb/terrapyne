"""BDD tests for cost estimate commands."""
import re
from unittest.mock import MagicMock

from pytest_bdd import given, parsers, scenario, then, when
import pytest
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.run import Run, RunStatus
from terrapyne.models.workspace import Workspace

runner = CliRunner()

@pytest.fixture
def mock_api_client():
    from unittest.mock import patch
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_ws_client, \
         patch("terrapyne.cli.project_cmd.TFCClient") as mock_prj_client, \
         patch("terrapyne.cli.workspace_cmd.validate_context") as mock_ws_ctx, \
         patch("terrapyne.cli.project_cmd.validate_context") as mock_prj_ctx:
        
        mock_instance = MagicMock()
        mock_ws_client.return_value.__enter__.return_value = mock_instance
        mock_prj_client.return_value = mock_instance
        mock_prj_client.return_value.__enter__.return_value = mock_instance
        
        def ws_validate(org, ws=None, **kwargs):
            return "test-org", ws

        def prj_validate(org, **kwargs):
            return "test-org", None
            
        mock_ws_ctx.side_effect = ws_validate
        mock_prj_ctx.side_effect = prj_validate
        
        yield mock_instance


@scenario("../features/costs.feature", "Extract workspace costs from the latest plan")
def test_workspace_costs() -> None:
    """Extract workspace costs from the latest plan."""
    pass


@scenario("../features/costs.feature", "Aggregate costs across a project")
def test_project_costs() -> None:
    """Aggregate costs across a project."""
    pass


# --- Given Steps ---

@given(parsers.parse('a Terraform Cloud workspace "{workspace_name}" exists'))
def workspace_exists(mock_api_client: MagicMock, workspace_name: str) -> None:
    """Mock a workspace existing."""
    ws = Workspace(
        id=f"ws-{workspace_name}",
        name=workspace_name,
        organization={"name": "test-org"},
        project={"id": "prj-test", "name": "Default Project"},
    )
    mock_api_client.workspaces.get_by_name.return_value = ws


@given(parsers.parse('the latest run for "{workspace_name}" has a cost estimate of ${monthly} monthly with a ${delta} delta'))
def latest_run_has_cost_estimate(mock_api_client: MagicMock, workspace_name: str, monthly: str, delta: str) -> None:
    """Mock the latest run with a cost estimate."""
    run = Run(
        id="run-costs-test",
        status=RunStatus.PLANNED,
        workspace={"id": f"ws-{workspace_name}", "name": workspace_name},
        cost_estimate={
            "proposed_monthly_cost": f"{monthly}.00",
            "delta_monthly_cost": f"{delta}.00"
        }
    )
    mock_api_client.runs.list.return_value = ([run], 1)


@given(parsers.parse('a Terraform Cloud project "{project_name}" exists'))
def project_exists(mock_api_client: MagicMock, project_name: str) -> None:
    """Mock a project existing."""
    from terrapyne.models.project import Project
    prj = Project(
        id=f"prj-{project_name}",
        name=project_name,
        organization={"name": "test-org"},
    )
    mock_api_client.projects.get_by_name.return_value = prj


@given(parsers.parse('the project "{project_name}" contains workspaces with cost estimates totaling ${total_monthly} monthly'))
def project_workspaces_have_cost_estimates(mock_api_client: MagicMock, project_name: str, total_monthly: str) -> None:
    """Mock a project with multiple workspaces and cost estimates."""
    # Simplified mock for the total project cost.
    mock_api_client.workspaces.list.return_value = (
        [Workspace(id="ws-1", name="ws-1"), Workspace(id="ws-2", name="ws-2")],
        2
    )
    
    def list_runs(workspace_id, **kwargs):
        if workspace_id == "ws-1":
            return ([Run(
                id="run-1", status=RunStatus.PLANNED,
                cost_estimate={"proposed_monthly_cost": str(int(total_monthly) // 2) + ".00", "delta_monthly_cost": "0.0"}
            )], 1)
        elif workspace_id == "ws-2":
            return ([Run(
                id="run-2", status=RunStatus.PLANNED,
                cost_estimate={"proposed_monthly_cost": str(int(total_monthly) - int(total_monthly) // 2) + ".00", "delta_monthly_cost": "0.0"}
            )], 1)
        return ([], 0)
        
    mock_api_client.runs.list.side_effect = list_runs


# --- When Steps ---

@when(parsers.parse('I run "{command}"'), target_fixture="cli_result")
def run_command(mock_api_client: MagicMock, command: str) -> object:
    """Run a CLI command."""
    args = command.replace("tfc ", "").split()
    return runner.invoke(app, args, catch_exceptions=False)


# --- Then Steps ---

@then("the command should succeed")
def command_succeeds(cli_result: object) -> None:
    """Check that the command succeeded."""
    assert cli_result.exit_code == 0, f"Command failed: {cli_result.stdout}"


@then(parsers.parse('the output should show an estimated monthly cost of "{expected_cost}"'))
def output_shows_monthly_cost(cli_result: object, expected_cost: str) -> None:
    """Check that the output contains the estimated monthly cost."""
    assert expected_cost in cli_result.stdout


@then(parsers.parse('the output should show a cost delta of "{expected_delta}"'))
def output_shows_cost_delta(cli_result: object, expected_delta: str) -> None:
    """Check that the output contains the cost delta."""
    assert expected_delta in cli_result.stdout


@then(parsers.parse('the output should show the total project estimated monthly cost of "{expected_cost}"'))
def output_shows_total_project_cost(cli_result: object, expected_cost: str) -> None:
    """Check that the output contains the total project estimated cost."""
    assert expected_cost in cli_result.stdout

