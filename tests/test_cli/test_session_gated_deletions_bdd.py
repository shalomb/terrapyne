"""BDD step definitions for session-gated deletions (ADR-007)."""

from __future__ import annotations

import shlex
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.cli.agent_context import AgentContext
from terrapyne.cli.main import app
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.workspace import Workspace

scenarios("../features/session_gated_deletions.feature")

runner = CliRunner()


@pytest.fixture
def mock_client():
    client = MagicMock()
    # Workspace mock
    mock_ws = MagicMock(spec=Workspace)
    mock_ws.id = "ws-123"
    mock_ws.name = "dev-sandbox"
    client.workspaces.get.return_value = mock_ws

    # Variables mock
    mock_var = MagicMock(spec=WorkspaceVariable)
    mock_var.id = "var-999"
    mock_var.key = "DB_PASSWORD"
    client.workspaces.get_variables.return_value = [mock_var]

    # HTTP request mock
    mock_resp = MagicMock()
    mock_resp.status_code = 204
    mock_resp.text = ""
    client._request.return_value = mock_resp
    return client


@pytest.fixture
def context_state():
    return {
        "env": {},
        "isatty": True,
        "is_agent": False,
        "result": None,
        "captured_subprocess": {},
    }


@given("the current execution context is an interactive human terminal")
def _human_context(context_state):
    context_state["env"] = {}
    context_state["isatty"] = True
    context_state["is_agent"] = False


@given("the current execution context is an automated agent session")
def _agent_context(context_state):
    context_state["env"] = {"CI": "true"}
    context_state["isatty"] = False
    context_state["is_agent"] = True


@given("no deletion grants are configured")
def _no_grants(context_state):
    context_state["env"].pop("TERRAPYNE_ALLOW_DELETE", None)


@given(parsers.parse('the active session grants deletion for "{grant}"'))
def _set_grant(context_state, grant):
    context_state["env"]["TERRAPYNE_ALLOW_DELETE"] = grant


@given(parsers.parse('a workspace named "{ws_name}" exists in the organization'))
def _mock_workspace_exists(mock_client, ws_name):
    mock_ws = MagicMock(spec=Workspace)
    mock_ws.id = f"ws-{ws_name}"
    mock_ws.name = ws_name
    mock_client.workspaces.get.return_value = mock_ws


@given(parsers.parse('a variable "{key}" exists on workspace "{ws_name}"'))
def _mock_variable_exists(mock_client, key, ws_name):
    mock_var = MagicMock(spec=WorkspaceVariable)
    mock_var.id = f"var-{key}"
    mock_var.key = key
    mock_client.workspaces.get_variables.return_value = [mock_var]


@when(parsers.parse('I run "{cli_command}"'))
def _run_cli_command(context_state, mock_client, cli_command):
    args = shlex.split(cli_command)
    # Strip binary prefix ('tfc' or 'terrapyne')
    if args and args[0] in ("tfc", "terrapyne"):
        args = args[1:]

    def fake_detect(env=None, stdout_isatty=None):
        if env is not None and "TERRAPYNE_ALLOW_DELETE" in env:
            # retain grant
            pass
        return AgentContext(
            is_agent=context_state["is_agent"],
            reason="test_agent" if context_state["is_agent"] else None,
        )

    def fake_subprocess_run(cmd, env=None, **kwargs):
        context_state["captured_subprocess"]["cmd"] = cmd
        context_state["captured_subprocess"]["env"] = env
        res = MagicMock()
        res.returncode = 0
        return res

    with (
        patch("terrapyne.cli.safety.agent_context.detect", side_effect=fake_detect),
        patch("terrapyne.cli.agent_context.detect", side_effect=fake_detect),
        patch("terrapyne.cli.context_helpers.get_client") as mock_get_client,
        patch("terrapyne.cli.workspace_cmd.get_client", mock_get_client),
        patch("terrapyne.cli.api_cmd.get_client", mock_get_client),
        patch("terrapyne.cli.workspace_cmd.resolve_organization", return_value="test-org"),
        patch(
            "terrapyne.cli.workspace_cmd.validate_context",
            side_effect=lambda org=None, ws=None, require_workspace=False: (
                org or "test-org",
                ws or "dev-sandbox",
            ),
        ),
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
        patch("subprocess.run", side_effect=fake_subprocess_run),
        patch.dict("os.environ", context_state["env"], clear=True),
    ):
        mock_get_client.return_value.__enter__.return_value = mock_client
        context_state["result"] = runner.invoke(app, args)


@then("the command succeeds")
def _check_succeeds(context_state):
    result = context_state["result"]
    assert result.exit_code == 0, f"Expected success, got {result.exit_code}: {result.output}"


@then(parsers.parse('the workspace "{ws_name}" is deleted via the API'))
def _check_ws_deleted(mock_client, ws_name):
    mock_client.workspaces.delete.assert_called_once()


@then("the command exits with refusal code 1")
def _check_refusal(context_state):
    result = context_state["result"]
    assert result.exit_code == 1


@then("no API deletion request was made")
def _check_no_api_calls(mock_client):
    mock_client.workspaces.delete.assert_not_called()
    mock_client.workspaces.delete_variable.assert_not_called()
    mock_client._request.assert_not_called()


@then(parsers.parse('stderr indicates deletion of "{resource}" is gated in agent sessions'))
def _check_stderr_refusal(context_state, resource):
    result = context_state["result"]
    combined = result.output + (result.stderr or "")
    assert f"Deletion of '{resource}' is gated in automated/agent sessions." in combined


@then(parsers.parse('the error hints suggest running with "{hint}"'))
def _check_error_hints(context_state, hint):
    result = context_state["result"]
    combined = result.output + (result.stderr or "")
    assert hint in combined


@then(parsers.parse('the variable "{key}" is removed via the API'))
def _check_var_removed(mock_client, key):
    mock_client.workspaces.delete_variable.assert_called_once()


@then(parsers.parse('the child process runs with "{grant}" deletion granted'))
def _check_child_grant(context_state, grant):
    env = context_state["captured_subprocess"]["env"]
    assert env is not None
    assert env.get("TERRAPYNE_ALLOW_DELETE") == grant
