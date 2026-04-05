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
        
        # Mock get_organization to return the organization name
        mock_instance.get_organization.return_value = "test-org"
        
        # Store projects and workspaces in a dict that can be updated by fixture steps
        # This allows steps to add data that will be returned by paginate_with_meta
        fixture_data = {"projects": {}, "workspaces": {}}
        
        def paginate_side_effect(path, params=None, **kwargs):
            """Mock paginate_with_meta that returns data based on what the steps have set up."""
            if params is None:
                params = {}
                
            # If searching for a project by name
            if "filter[names]" in params:
                name = params["filter[names]"]
                if name in fixture_data["projects"]:
                    prj_data = fixture_data["projects"][name]
                    # prj_data is already in API response format (dict), return it as is
                    return (iter([prj_data]), 1)
            
            # Default: return empty
            return (iter([]), 0)
        
        mock_instance.paginate_with_meta.side_effect = paginate_side_effect
        # Also store fixture_data on the mock for steps to access
        mock_instance._fixture_data = fixture_data
        
        def ws_validate(org, ws=None, **kwargs):
            return "test-org", ws

        def prj_validate(org, **kwargs):
            return "test-org", None
            
        mock_ws_ctx.side_effect = ws_validate
        mock_prj_ctx.side_effect = prj_validate
        
        yield mock_instance

@scenario("../features/costs.feature", "Extract workspace costs from the latest plan")
def test_workspace_costs() -> None:
    pass

@scenario("../features/costs.feature", "Extract workspace costs with a cost decrease")
def test_workspace_costs_decrease() -> None:
    pass

@scenario("../features/costs.feature", "Extract workspace costs with zero delta")
def test_workspace_costs_zero() -> None:
    pass

@scenario("../features/costs.feature", "Extract workspace costs when no cost estimate is available")
def test_workspace_costs_no_estimate() -> None:
    pass

@scenario("../features/costs.feature", "Extract workspace costs with invalid cost strings")
def test_workspace_costs_invalid() -> None:
    pass

@scenario("../features/costs.feature", "Aggregate costs across a project")
def test_project_costs() -> None:
    pass

@scenario("../features/costs.feature", "Aggregate costs across a project with no workspaces")
def test_project_costs_empty() -> None:
    pass

@scenario("../features/costs.feature", "Aggregate costs across a project with invalid cost strings")
def test_project_costs_invalid() -> None:
    pass

# --- Given Steps ---

@given(parsers.parse('a Terraform Cloud workspace "{workspace_name}" exists'))
def workspace_exists(mock_api_client: MagicMock, workspace_name: str) -> None:
    ws = Workspace(
        id=f"ws-{workspace_name}",
        name=workspace_name,
        organization={"name": "test-org"},
        project={"id": "prj-test", "name": "Default Project"},
    )
    mock_api_client.workspaces.get_by_name.return_value = ws

@given(parsers.parse('the latest run for "{workspace_name}" has a cost estimate of ${monthly} monthly with a ${delta} delta'))
def latest_run_has_cost_estimate(mock_api_client: MagicMock, workspace_name: str, monthly: str, delta: str) -> None:
    mock_api_client.runs.get_latest_cost_estimate.return_value = {
        "proposed-monthly-cost": f"{monthly}.00", "prior-monthly-cost": "0.0", "delta-monthly-cost": f"{delta}.00", "matched-resources-count": 1, "unmatched-resources-count": 0, "resources": {"matched": [], "unmatched": []},
        "delta": f"{delta}.00"
    }

@given(parsers.parse('the latest run for "{workspace_name}" has a cost estimate of ${monthly} monthly with a -${delta} delta'))
def latest_run_has_cost_estimate_decrease(mock_api_client: MagicMock, workspace_name: str, monthly: str, delta: str) -> None:
    mock_api_client.runs.get_latest_cost_estimate.return_value = {
        "proposed-monthly-cost": f"{monthly}.00", "prior-monthly-cost": "0.0", "delta-monthly-cost": f"-{delta}.00", "matched-resources-count": 1, "unmatched-resources-count": 0, "resources": {"matched": [], "unmatched": []}
    }

@given(parsers.parse('the latest run for "{workspace_name}" has no cost estimate'))
def latest_run_no_cost_estimate(mock_api_client: MagicMock, workspace_name: str) -> None:
    mock_api_client.runs.get_latest_cost_estimate.return_value = None

@given(parsers.parse('the latest run for "{workspace_name}" has an invalid cost estimate string'))
def latest_run_invalid_cost_estimate(mock_api_client: MagicMock, workspace_name: str) -> None:
    mock_api_client.runs.get_latest_cost_estimate.return_value = {
        "proposed-monthly-cost": "invalid_cost", "prior-monthly-cost": "0.0", "delta-monthly-cost": "invalid_delta", "matched-resources-count": 0, "unmatched-resources-count": 0, "resources": {"matched": [], "unmatched": []}
    }

@given(parsers.parse('a Terraform Cloud project "{project_name}" exists'))
def project_exists(mock_api_client: MagicMock, project_name: str) -> None:
    # Create project data in API response format (with attributes)
    prj_api_response = {
        "id": f"prj-{project_name}",
        "type": "projects",
        "attributes": {
            "name": project_name,
            "description": None,
            "created-at": None,
            "resource-count": 0,
        }
    }
    
    # Also create the model version for get_by_name
    from terrapyne.models.project import Project
    prj_model = Project.from_api_response(prj_api_response)
    
    # Store in fixture data so paginate_with_meta can find it
    mock_api_client._fixture_data["projects"][project_name] = prj_api_response
    
    # Also mock the direct get_by_name call as a fallback
    mock_api_client.projects.get_by_name.return_value = prj_model

@given(parsers.parse('the project "{project_name}" contains workspaces with cost estimates totaling ${total_monthly} monthly'))
def project_workspaces_have_cost_estimates(mock_api_client: MagicMock, project_name: str, total_monthly: str) -> None:
    mock_api_client.workspaces.list.return_value = (
        [Workspace(id="ws-1", name="ws-1"), Workspace(id="ws-2", name="ws-2")],
        2
    )
    
    def get_costs(workspace_id, **kwargs):
        if workspace_id == "ws-1":
            return {"proposed-monthly-cost": str(int(total_monthly) // 2) + ".00", "delta-monthly-cost": "0.0", "matched-resources-count": 0, "unmatched-resources-count": 0, "resources": {"matched": [], "unmatched": []}}
        elif workspace_id == "ws-2":
            return {"proposed-monthly-cost": str(int(total_monthly) - int(total_monthly) // 2) + ".00", "delta-monthly-cost": "0.0", "matched-resources-count": 0, "unmatched-resources-count": 0, "resources": {"matched": [], "unmatched": []}}
        return None
        
    mock_api_client.runs.get_latest_cost_estimate.side_effect = get_costs

@given(parsers.parse('the project "{project_name}" contains workspaces with invalid cost estimates'))
def project_workspaces_invalid_cost_estimates(mock_api_client: MagicMock, project_name: str) -> None:
    mock_api_client.workspaces.list.return_value = (
        [Workspace(id="ws-1", name="ws-1")],
        1
    )
    mock_api_client.runs.get_latest_cost_estimate.return_value = {
        "proposed-monthly-cost": "invalid_string", "delta-monthly-cost": "0.0", "matched-resources-count": 0, "unmatched-resources-count": 0, "resources": {"matched": [], "unmatched": []}
    }

@given(parsers.parse('the project "{project_name}" contains no workspaces'))
def project_contains_no_workspaces(mock_api_client: MagicMock, project_name: str) -> None:
    mock_api_client.workspaces.list.return_value = ([], 0)

# --- When Steps ---

@when(parsers.parse('I run "{command}"'), target_fixture="cli_result")
def run_command(mock_api_client: MagicMock, command: str) -> object:
    args = command.replace("tfc ", "").split()
    return runner.invoke(app, args, catch_exceptions=False)

# --- Then Steps ---

@then("the command should succeed")
def command_succeeds(cli_result: object) -> None:
    assert cli_result.exit_code == 0, f"Command failed: {cli_result.stdout}"

@then(parsers.parse('the output should show an estimated monthly cost of "{expected_cost}"'))
def output_shows_monthly_cost(cli_result: object, expected_cost: str) -> None:
    assert expected_cost in cli_result.stdout

@then(parsers.parse('the output should show a cost delta of "{expected_delta}"'))
def output_shows_cost_delta(cli_result: object, expected_delta: str) -> None:
    assert expected_delta in cli_result.stdout

@then("the output should indicate no cost estimates are available")
def output_indicates_no_cost_estimates(cli_result: object) -> None:
    assert "No finished cost estimates" in cli_result.stdout

@then(parsers.parse('the output should show the total project estimated monthly cost of "{expected_cost}"'))
def output_shows_total_project_cost(cli_result: object, expected_cost: str) -> None:
    # Remove formatting (commas) from both expected and actual for comparison
    normalized_expected = expected_cost.replace(",", "")
    normalized_stdout = cli_result.stdout.replace(",", "")
    assert normalized_expected in normalized_stdout
