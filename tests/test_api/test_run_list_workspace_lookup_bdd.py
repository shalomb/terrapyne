"""BDD step definitions for run list workspace name lookup (B9)."""

from unittest.mock import MagicMock, patch

from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.cli.main import app
from tests.fixtures.factories import workspace_response

scenarios("../features/run_list_workspace_lookup.feature")

runner = CliRunner()


# ---------------------------------------------------------------------------
# Givens
# ---------------------------------------------------------------------------


@given("a terraform cloud organization is accessible", target_fixture="org")
def org_accessible():
    return "test-org"


@given('workspace "my-app-dev" exists in the organization', target_fixture="lookup_context")
def ws_simple_exists(org):
    return {"name": "my-app-dev", "id": "ws-abc123", "org": org}


@given(
    'workspace "tec-dce-inn-dev-93400-shalombhooshi" exists in the organization',
    target_fixture="lookup_context",
)
def ws_hyphenated_exists(org):
    return {"name": "tec-dce-inn-dev-93400-shalombhooshi", "id": "ws-tecdce", "org": org}


@given(
    'workspace "non-existent-ws" does not exist in the organization',
    target_fixture="lookup_context",
)
def ws_missing(org):
    return {"name": "non-existent-ws", "id": None, "org": org}


# ---------------------------------------------------------------------------
# Whens
# ---------------------------------------------------------------------------


@when('I run "tfc run list --workspace my-app-dev"', target_fixture="cli_result")
def run_list_simple(lookup_context):
    return _invoke_run_list(lookup_context)


@when(
    'I run "tfc run list --workspace tec-dce-inn-dev-93400-shalombhooshi"',
    target_fixture="cli_result",
)
def run_list_hyphenated(lookup_context):
    return _invoke_run_list(lookup_context)


@when("the workspace API fetches the workspace by name", target_fixture="api_call_result")
def api_fetches_by_name(lookup_context):
    client = MagicMock()
    client.get_organization.return_value = lookup_context["org"]
    resp = workspace_response(name=lookup_context["name"], id=lookup_context["id"])
    client.get.return_value = {**resp, "included": []}
    api = WorkspaceAPI(client)
    ws = api.get(lookup_context["name"], organization=lookup_context["org"])
    return {"client": client, "ws": ws, "context": lookup_context}


@when('I run "tfc run list --workspace non-existent-ws"', target_fixture="cli_result")
def run_list_missing(lookup_context):
    from terrapyne.api.client import TFCAPIError

    with (
        patch("terrapyne.cli.context_helpers.validate_context") as mock_ctx,
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_ctx.return_value = (lookup_context["org"], lookup_context["name"])
        mock_instance = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.side_effect = TFCAPIError(
            "Workspace not found", status_code=404
        )
        return runner.invoke(
            app,
            [
                "run",
                "list",
                "--workspace",
                lookup_context["name"],
                "--organization",
                lookup_context["org"],
            ],
        )


def _invoke_run_list(lookup_context):
    ws_resp = workspace_response(name=lookup_context["name"], id=lookup_context["id"])
    from terrapyne.models.workspace import Workspace

    ws_model = Workspace.from_api_response(ws_resp["data"])

    with (
        patch("terrapyne.cli.context_helpers.validate_context") as mock_ctx,
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_ctx.return_value = (lookup_context["org"], lookup_context["name"])
        mock_instance = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.return_value = ws_model
        mock_instance.runs.list.return_value = ([], 0)
        return runner.invoke(
            app,
            [
                "run",
                "list",
                "--workspace",
                lookup_context["name"],
                "--organization",
                lookup_context["org"],
            ],
        )


# ---------------------------------------------------------------------------
# Thens
# ---------------------------------------------------------------------------


@then('the workspace should be resolved by name "my-app-dev"')
def resolved_simple(cli_result):
    assert cli_result.exit_code == 0, f"exit {cli_result.exit_code}: {cli_result.stdout}"


@then('the workspace should be resolved by name "tec-dce-inn-dev-93400-shalombhooshi"')
def resolved_hyphenated(cli_result):
    assert cli_result.exit_code == 0, f"exit {cli_result.exit_code}: {cli_result.stdout}"


@then("runs should be fetched using the workspace ID")
def runs_fetched_by_id(cli_result):
    assert cli_result.exit_code == 0, f"exit {cli_result.exit_code}: {cli_result.stdout}"


@then("exit code should be 0")
def exit_0(cli_result):
    assert cli_result.exit_code == 0, f"exit {cli_result.exit_code}: {cli_result.stdout}"


@then('it should use the direct endpoint "/organizations/{org}/workspaces/{name}"')
def uses_direct_endpoint(api_call_result):
    client = api_call_result["client"]
    path = client.get.call_args[0][0]
    ws_name = api_call_result["context"]["name"]
    org = api_call_result["context"]["org"]
    assert path == f"/organizations/{org}/workspaces/{ws_name}"


@then("it should NOT use search[name] which returns partial matches")
def no_fuzzy_search(api_call_result):
    client = api_call_result["client"]
    params = client.get.call_args[1].get("params", {})
    assert "search[name]" not in params
    assert "filter[names]" not in params


@then('I should see an error message containing "not found"')
def error_not_found(cli_result):
    output = cli_result.stdout.lower()
    assert "not found" in output or "error" in output, f"expected error in: {cli_result.stdout}"


@then("exit code should be 1")
def exit_1(cli_result):
    assert cli_result.exit_code == 1, f"exit {cli_result.exit_code}: {cli_result.stdout}"
