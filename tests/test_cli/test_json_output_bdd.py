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


# --- Scenarios ---

@scenario("../features/json_output.feature", "Workspace listing produces parseable JSON")
def test_workspace_list_json():
    pass


@scenario("../features/json_output.feature", "Run listing produces parseable JSON")
def test_run_list_json():
    pass


@scenario("../features/json_output.feature", "Project listing produces parseable JSON")
def test_project_list_json():
    pass


@scenario("../features/json_output.feature", "Team listing produces parseable JSON")
def test_team_list_json():
    pass


@scenario("../features/json_output.feature", "Workspace detail produces a JSON object")
def test_workspace_show_json():
    pass


@scenario("../features/json_output.feature", "Run detail produces a JSON object")
def test_run_show_json():
    pass


# --- Given ---

@given("workspaces exist in the organization", target_fixture="mock_client")
def workspaces_exist():
    mock = MagicMock()
    ws = Workspace.model_construct(
        id="ws-abc123", name="my-app-dev", terraform_version="1.9.0",
        created_at=None, updated_at=None, auto_apply=False,
        execution_mode="remote", locked=False, tag_names=[], project_id=None,
    )
    mock.workspaces.list.return_value = (iter([ws]), 1)
    return mock


@given("a workspace with runs", target_fixture="mock_client")
def workspace_with_runs():
    mock = MagicMock()
    ws = Workspace.model_construct(id="ws-abc123", name="my-app-dev")
    mock.workspaces.get.return_value = ws
    run = Run.model_construct(
        id="run-xyz789", status=RunStatus("applied"), message="deploy",
        created_at=None, updated_at=None, resource_additions=1,
        resource_changes=0, resource_destructions=0, workspace_id="ws-abc123",
    )
    mock.runs.list.return_value = ([run], 1)
    return mock


@given("projects exist in the organization", target_fixture="mock_client")
def projects_exist():
    mock = MagicMock()
    proj = Project.model_construct(id="prj-abc", name="my-project", created_at=None, resource_count=5)
    mock_api = MagicMock()
    mock_api.list.return_value = (iter([proj]), 1)
    mock_api.get_workspace_counts.return_value = {}
    mock.projects = mock_api
    return mock


@given("teams exist in the organization", target_fixture="mock_client")
def teams_exist():
    mock = MagicMock()
    team = Team.model_construct(id="team-abc", name="platform-devs", created_at=None)
    mock.teams.list_teams.return_value = (iter([team]), 1)
    return mock


@given(parsers.parse('workspace "{name}" exists'), target_fixture="mock_client")
def workspace_exists(name):
    mock = MagicMock()
    ws = Workspace.model_construct(
        id="ws-abc123", name=name, terraform_version="1.9.0",
        created_at=None, updated_at=None, auto_apply=False,
        execution_mode="remote", locked=False, tag_names=[], project_id=None,
    )
    mock.workspaces.get.return_value = ws
    mock.workspaces.get_variables.return_value = []
    return mock


@given(parsers.parse('a run "{run_id}" exists'), target_fixture="mock_client")
def run_exists(run_id):
    mock = MagicMock()
    run = Run.model_construct(
        id=run_id, status=RunStatus("applied"), message="deploy",
        created_at=None, updated_at=None, resource_additions=2,
        resource_changes=1, resource_destructions=0, workspace_id="ws-abc123",
        plan_id="plan-123",
    )
    mock.runs.get.return_value = run
    mock.runs.get_plan.return_value = MagicMock(
        additions=2, changes=1, destructions=0, resource_count=3
    )
    ws = Workspace.model_construct(id="ws-abc123", name="my-app-dev")
    mock.workspaces.get_by_id.return_value = ws
    return mock


# --- When ---

@when("I request the workspace list as JSON", target_fixture="cli_result")
def request_workspace_list_json(mock_client):
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as cls:
        cls.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["workspace", "list", "-o", "test-org", "--format", "json"])


@when("I request the run list as JSON", target_fixture="cli_result")
def request_run_list_json(mock_client):
    with patch("terrapyne.cli.run_cmd.TFCClient") as cls:
        cls.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["run", "list", "-w", "my-app-dev", "-o", "test-org", "--format", "json"])


@when("I request the project list as JSON", target_fixture="cli_result")
def request_project_list_json(mock_client):
    with patch("terrapyne.cli.project_cmd.TFCClient") as cls, \
         patch("terrapyne.cli.project_cmd.ProjectAPI") as api_cls:
        api_cls.return_value = mock_client.projects
        cls.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["project", "list", "-o", "test-org", "--format", "json"])


@when("I request the team list as JSON", target_fixture="cli_result")
def request_team_list_json(mock_client):
    with patch("terrapyne.cli.team_cmd.TFCClient") as cls:
        cls.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["team", "list", "-o", "test-org", "--format", "json"])


@when("I request the workspace detail as JSON", target_fixture="cli_result")
def request_workspace_show_json(mock_client):
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as cls:
        cls.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["workspace", "show", "my-app-dev", "-o", "test-org", "--format", "json"])


@when("I request the run detail as JSON", target_fixture="cli_result")
def request_run_show_json(mock_client):
    with patch("terrapyne.cli.run_cmd.TFCClient") as cls:
        cls.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["run", "show", "run-abc123", "-o", "test-org", "--format", "json"])


# --- Then ---

@then("the output is valid JSON")
def output_is_valid_json(cli_result):
    assert cli_result.exit_code == 0, f"Exit code {cli_result.exit_code}: {cli_result.stdout}"
    json.loads(cli_result.stdout)


@then(parsers.parse('each workspace has an "id" and "name"'))
def each_workspace_has_fields(cli_result):
    data = json.loads(cli_result.stdout)
    for item in data:
        assert "id" in item
        assert "name" in item


@then(parsers.parse('each run has an "id" and "status"'))
def each_run_has_fields(cli_result):
    data = json.loads(cli_result.stdout)
    for item in data:
        assert "id" in item
        assert "status" in item


@then(parsers.parse('each team has an "id" and "name"'))
def each_team_has_fields(cli_result):
    data = json.loads(cli_result.stdout)
    for item in data:
        assert "id" in item
        assert "name" in item


@then(parsers.parse('the result is a JSON object with key "id"'))
def result_is_object_with_id(cli_result):
    data = json.loads(cli_result.stdout)
    assert isinstance(data, dict)
    assert "id" in data
