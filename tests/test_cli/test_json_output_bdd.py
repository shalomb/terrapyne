"""BDD steps for machine-readable JSON output."""
import json
from unittest.mock import MagicMock, patch
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner
from terrapyne.cli.main import app
from terrapyne.models.project import Project
from terrapyne.models.run import Run, RunStatus
from terrapyne.models.team import Team
from terrapyne.models.workspace import Workspace
runner = CliRunner()

@scenario("../features/json_output.feature", "Workspace listing produces parseable JSON")
def test_workspace_list_json(): pass
@scenario("../features/json_output.feature", "Run listing produces parseable JSON")
def test_run_list_json(): pass
@scenario("../features/json_output.feature", "Project listing produces parseable JSON")
def test_project_list_json(): pass
@scenario("../features/json_output.feature", "Team listing produces parseable JSON")
def test_team_list_json(): pass
@scenario("../features/json_output.feature", "Workspace detail produces a JSON object")
def test_workspace_show_json(): pass
@scenario("../features/json_output.feature", "Run detail produces a JSON object")
def test_run_show_json(): pass

@given("workspaces exist in the organization", target_fixture="mock_client")
def workspaces_exist():
    m = MagicMock()
    m.workspaces.list.return_value = (iter([Workspace.model_construct(id="ws-abc", name="my-app-dev", terraform_version="1.9.0", created_at=None, updated_at=None, auto_apply=False, execution_mode="remote", locked=False, tag_names=[], project_id=None)]), 1)
    return m

@given("a workspace with runs", target_fixture="mock_client")
def workspace_with_runs():
    m = MagicMock()
    m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="my-app-dev")
    m.runs.list.return_value = ([Run.model_construct(id="run-xyz", status=RunStatus("applied"), message="deploy", created_at=None, updated_at=None, resource_additions=1, resource_changes=0, resource_destructions=0, workspace_id="ws-abc")], 1)
    return m

@given("projects exist in the organization", target_fixture="mock_client")
def projects_exist():
    m = MagicMock()
    api = MagicMock()
    api.list.return_value = (iter([Project.model_construct(id="prj-1", name="proj", created_at=None, resource_count=5)]), 1)
    api.get_workspace_counts.return_value = {}
    m.projects = api
    return m

@given("teams exist in the organization", target_fixture="mock_client")
def teams_exist():
    m = MagicMock()
    m.teams.list_teams.return_value = (iter([Team.model_construct(id="team-1", name="devs", created_at=None)]), 1)
    return m

@given(parsers.parse('workspace "{name}" exists'), target_fixture="mock_client")
def workspace_named(name):
    m = MagicMock()
    m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name=name, terraform_version="1.9.0", created_at=None, updated_at=None, auto_apply=False, execution_mode="remote", locked=False, tag_names=[], project_id=None)
    m.workspaces.get_variables.return_value = []
    m.runs.list.return_value = ([], 0)
    return m

@given(parsers.parse('a run "{run_id}" exists'), target_fixture="mock_client")
def run_named(run_id):
    m = MagicMock()
    m.runs.get.return_value = Run.model_construct(id=run_id, status=RunStatus("applied"), message="deploy", created_at=None, updated_at=None, resource_additions=2, resource_changes=1, resource_destructions=0, workspace_id="ws-abc", plan_id="plan-1")
    m.runs.get_plan.return_value = MagicMock(additions=2, changes=1, destructions=0)
    m.workspaces.get_by_id.return_value = Workspace.model_construct(id="ws-abc", name="my-app-dev")
    return m

@when("I request the workspace list as JSON", target_fixture="cli_result")
def req_ws_list(mock_client):
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as c:
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["workspace", "list", "-o", "test-org", "--format", "json"])

@when("I request the run list as JSON", target_fixture="cli_result")
def req_run_list(mock_client):
    with patch("terrapyne.cli.run_cmd.TFCClient") as c:
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["run", "list", "-w", "my-app-dev", "-o", "test-org", "--format", "json"])

@when("I request the project list as JSON", target_fixture="cli_result")
def req_proj_list(mock_client):
    with patch("terrapyne.cli.project_cmd.TFCClient") as c, patch("terrapyne.cli.project_cmd.ProjectAPI") as a:
        a.return_value = mock_client.projects
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["project", "list", "-o", "test-org", "--format", "json"])

@when("I request the team list as JSON", target_fixture="cli_result")
def req_team_list(mock_client):
    with patch("terrapyne.cli.team_cmd.TFCClient") as c:
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["team", "list", "-o", "test-org", "--format", "json"])

@when("I request the workspace detail as JSON", target_fixture="cli_result")
def req_ws_show(mock_client):
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as c, \
         patch("terrapyne.cli.workspace_cmd.validate_context") as v:
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["workspace", "show", "my-app-dev", "-o", "test-org", "--format", "json"])

@when("I request the run detail as JSON", target_fixture="cli_result")
def req_run_show(mock_client):
    with patch("terrapyne.cli.run_cmd.TFCClient") as c:
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["run", "show", "run-abc123", "-o", "test-org", "--format", "json"])

@then("the output is valid JSON")
def valid_json(cli_result):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.stdout}"
    json.loads(cli_result.stdout)

@then(parsers.parse('each workspace has an "id" and "name"'))
def ws_fields(cli_result):
    for item in json.loads(cli_result.stdout): assert "id" in item and "name" in item

@then(parsers.parse('each run has an "id" and "status"'))
def run_fields(cli_result):
    for item in json.loads(cli_result.stdout): assert "id" in item and "status" in item

@then(parsers.parse('each team has an "id" and "name"'))
def team_fields(cli_result):
    for item in json.loads(cli_result.stdout): assert "id" in item and "name" in item

@then(parsers.parse('the result is a JSON object with key "id"'))
def obj_with_id(cli_result):
    data = json.loads(cli_result.stdout)
    assert isinstance(data, dict) and "id" in data
