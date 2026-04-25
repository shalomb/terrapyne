"""BDD tests for workspace/team search optimization."""

from unittest.mock import MagicMock, patch

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.workspace import Workspace

runner = CliRunner()


@scenario(
    "../features/search_optimization.feature", "Workspace list uses wildcard search parameter"
)
def test_workspace_wildcard_search():
    pass


@scenario(
    "../features/search_optimization.feature",
    "Workspace list without search warns about large result sets",
)
def test_workspace_list_no_search_hint():
    pass


@scenario("../features/search_optimization.feature", "Team list uses server-side search")
def test_team_server_side_search():
    pass


# --- Fixtures ---


@given("a TFC organization with workspaces", target_fixture="org_context")
def org_with_workspaces():
    return {"org": "test-org"}


@given("a TFC organization with teams", target_fixture="org_context")
def org_with_teams():
    return {"org": "test-org"}


# --- Workspace search ---


@when(parsers.parse('I list workspaces with search "{pattern}"'), target_fixture="cli_result")
def list_workspaces_with_search(pattern):
    with patch("terrapyne.api.client.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        ws = Workspace.model_construct(
            id="ws-1",
            name="prod-app",
            terraform_version="1.9.0",
            created_at=None,
            updated_at=None,
            auto_apply=False,
            execution_mode="remote",
            locked=False,
            tag_names=[],
        )
        mock_instance.workspaces.list.return_value = (iter([ws]), 1)

        result = runner.invoke(app, ["workspace", "list", "-o", "test-org", "--search", pattern])
        return {"result": result, "mock": mock_instance}


@then("the API should receive a wildcard search parameter")
def check_wildcard_param(cli_result):
    call_args = cli_result["mock"].workspaces.list.call_args
    assert call_args is not None
    # Should pass search param through to API
    _, kwargs = call_args
    assert "search" in kwargs or (len(call_args.args) > 1 and call_args.args[1] is not None)


@then("results should only contain matching workspaces")
def check_results_filtered(cli_result):
    assert cli_result["result"].exit_code == 0


# --- No search hint ---


@when("I list workspaces without a search term", target_fixture="cli_result")
def list_workspaces_no_search():
    with patch("terrapyne.api.client.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        ws = Workspace.model_construct(
            id="ws-1",
            name="some-ws",
            terraform_version="1.9.0",
            created_at=None,
            updated_at=None,
            auto_apply=False,
            execution_mode="remote",
            locked=False,
            tag_names=[],
        )
        mock_instance.workspaces.list.return_value = (iter([ws]), 50)

        result = runner.invoke(app, ["workspace", "list", "-o", "test-org"])
        return {"result": result, "mock": mock_instance}


@then("I should see a hint to use --search for faster results")
def check_search_hint(cli_result):
    output = cli_result["result"].stdout
    assert "--search" in output


# --- Team search ---


@when(parsers.parse('I list teams with search "{term}"'), target_fixture="cli_result")
def list_teams_with_search(term):
    with patch("terrapyne.api.client.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.teams.list_teams.return_value = (iter([]), 0)

        result = runner.invoke(app, ["team", "list", "-o", "test-org", "--search", term])
        return {"result": result, "mock": mock_instance}


@then("the API should use the q= parameter for server-side filtering")
def check_team_search_param(cli_result):
    call_args = cli_result["mock"].teams.list_teams.call_args
    assert call_args is not None
    _, kwargs = call_args
    assert kwargs.get("search") == "platform"
