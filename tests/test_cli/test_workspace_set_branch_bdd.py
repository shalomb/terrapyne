"""BDD step definitions for workspace set-branch command (F13)."""

from unittest.mock import MagicMock, patch

from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.cli.main import app
from tests.fixtures.factories import workspace_response

scenarios("../features/workspace_set_branch.feature")

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ws_model(name="my-app-dev", branch="main", with_vcs=True):
    from terrapyne.models.workspace import Workspace

    vcs = (
        {
            "identifier": "myorg/my-app",
            "branch": branch,
            "repository-http-url": "https://github.com/myorg/my-app",
            "oauth-token-id": "ot-abc123",
        }
        if with_vcs
        else None
    )
    resp = workspace_response(name=name, vcs_repo=vcs)
    return Workspace.from_api_response(resp["data"])


# ---------------------------------------------------------------------------
# Givens
# ---------------------------------------------------------------------------


@given('workspace "my-app-dev" is in organization "test-org"', target_fixture="ws_context")
def ws_in_org():
    return {"workspace": "my-app-dev", "org": "test-org"}


@given('workspace "no-vcs-ws" is in organization "test-org"', target_fixture="ws_context")
def no_vcs_ws_in_org():
    return {"workspace": "no-vcs-ws", "org": "test-org"}


@given('the workspace has a VCS repository connected on branch "main"', target_fixture="mock_api")
def ws_has_vcs(ws_context):
    updated = _make_ws_model(ws_context["workspace"], branch="feature/my-change")
    mock = MagicMock()
    mock.workspaces.set_vcs_branch.return_value = updated
    return mock


@given("the workspace has no VCS repository connected", target_fixture="mock_api")
def ws_no_vcs(ws_context):
    mock = MagicMock()
    mock.workspaces.set_vcs_branch.side_effect = ValueError(
        f"Workspace '{ws_context['workspace']}' has no VCS connection."
    )
    return mock


@given("a WorkspaceAPI instance", target_fixture="api_context")
def api_instance():
    client = MagicMock()
    client.get_organization.return_value = "test-org"
    resp = workspace_response(
        name="my-app-dev",
        vcs_repo={"identifier": "myorg/my-app", "branch": "main", "oauth-token-id": "ot-1"},
    )
    updated_data = resp["data"].copy()
    updated_data["attributes"] = dict(updated_data["attributes"])
    updated_data["attributes"]["vcs-repo"] = dict(updated_data["attributes"]["vcs-repo"])
    updated_data["attributes"]["vcs-repo"]["branch"] = "feature/test"
    client.get.return_value = resp
    client.patch.return_value = {"data": updated_data}
    return {"client": client, "api": WorkspaceAPI(client)}


# ---------------------------------------------------------------------------
# Whens
# ---------------------------------------------------------------------------


@when(
    'I run "tfc workspace set-branch my-app-dev feature/my-change --organization test-org"',
    target_fixture="cli_result",
)
def run_set_branch_success(ws_context, mock_api):
    with (
        patch("terrapyne.cli.workspace_cmd.resolve_organization", return_value=ws_context["org"]),
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_cls.return_value.__enter__.return_value = mock_api
        return runner.invoke(
            app,
            [
                "workspace",
                "set-branch",
                ws_context["workspace"],
                "feature/my-change",
                "--organization",
                ws_context["org"],
            ],
        )


@when(
    'I run "tfc workspace set-branch no-vcs-ws feature/new --organization test-org"',
    target_fixture="cli_result",
)
def run_set_branch_no_vcs(ws_context, mock_api):
    with (
        patch("terrapyne.cli.workspace_cmd.resolve_organization", return_value=ws_context["org"]),
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_cls.return_value.__enter__.return_value = mock_api
        return runner.invoke(
            app,
            [
                "workspace",
                "set-branch",
                ws_context["workspace"],
                "feature/new",
                "--organization",
                ws_context["org"],
            ],
        )


@when(
    'I run "tfc workspace set-branch my-app-dev hotfix/123" without --organization',
    target_fixture="cli_result",
)
def run_set_branch_no_org(ws_context, mock_api):
    with (
        patch("terrapyne.cli.workspace_cmd.resolve_organization", return_value="test-org"),
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_cls.return_value.__enter__.return_value = mock_api
        return runner.invoke(
            app, ["workspace", "set-branch", ws_context["workspace"], "hotfix/123"]
        )


@when(
    'I call set_vcs_branch("my-app-dev", "feature/test", organization="test-org")',
    target_fixture="patch_result",
)
def call_set_vcs_branch(api_context):
    api_context["api"].set_vcs_branch("my-app-dev", "feature/test", organization="test-org")
    return api_context


# ---------------------------------------------------------------------------
# Thens
# ---------------------------------------------------------------------------


@then('the API should PATCH vcs-repo.branch to "feature/my-change"')
def api_patched_feature_branch(mock_api):
    mock_api.workspaces.set_vcs_branch.assert_called_once()
    call_kwargs = mock_api.workspaces.set_vcs_branch.call_args
    assert call_kwargs.kwargs["branch"] == "feature/my-change"


@then('the output should show the updated branch "feature/my-change"')
def output_shows_branch(cli_result):
    assert "feature/my-change" in cli_result.stdout, cli_result.stdout


@then("exit code should be 0")
def exit_0(cli_result):
    assert cli_result.exit_code == 0, f"exit {cli_result.exit_code}: {cli_result.stdout}"


@then('I should see error message containing "no VCS"')
def error_no_vcs(cli_result):
    assert "no VCS" in cli_result.stdout or "VCS" in cli_result.stdout, cli_result.stdout


@then("exit code should be 1")
def exit_1(cli_result):
    assert cli_result.exit_code == 1, f"exit {cli_result.exit_code}: {cli_result.stdout}"


@then('the API should PATCH vcs-repo.branch to "hotfix/123"')
def api_patched_hotfix(mock_api):
    mock_api.workspaces.set_vcs_branch.assert_called_once()
    call_kwargs = mock_api.workspaces.set_vcs_branch.call_args
    assert call_kwargs.kwargs["branch"] == "hotfix/123"


@then('the client should PATCH "/organizations/test-org/workspaces/my-app-dev"')
def client_patched_correct_path(patch_result):
    client = patch_result["client"]
    client.patch.assert_called_once()
    path = client.patch.call_args[0][0]
    assert path == "/organizations/test-org/workspaces/my-app-dev"


@then('the payload should have vcs-repo.branch set to "feature/test"')
def payload_has_branch(patch_result):
    client = patch_result["client"]
    payload = client.patch.call_args[1]["json_data"]
    assert payload["data"]["attributes"]["vcs-repo"]["branch"] == "feature/test"
    assert list(payload["data"]["attributes"]["vcs-repo"].keys()) == ["branch"]
