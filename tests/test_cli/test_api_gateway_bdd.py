"""BDD step definitions for tfc api gateway."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app

scenarios("../features/api_gateway.feature")

runner = CliRunner()


@pytest.fixture
def mock_client():
    client = MagicMock()
    # Default mock response object
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {}
    client._request.return_value = mock_resp
    return client


@pytest.fixture
def context_state():
    return {"org": None, "captured_request": {}}


@given(parsers.parse('the TFC API returns a workspace configuration for "{workspace}" in "{org}"'))
def _mock_workspace_config(mock_client, workspace, org):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    payload = {
        "data": {
            "id": f"ws-{workspace}",
            "type": "workspaces",
            "attributes": {"name": workspace, "organization": org},
        }
    }
    mock_resp.text = json.dumps(payload)
    mock_resp.json.return_value = payload
    mock_client._request.return_value = mock_resp


@given(parsers.parse('the local workspace context resolves organization "{org}"'))
def _mock_detected_org(context_state, org):
    context_state["org"] = org


@given(parsers.parse('the TFC API returns a list of workspaces for "{org}"'))
def _mock_workspaces_list(mock_client, org):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    payload = {"data": [{"id": "ws-1", "type": "workspaces", "attributes": {"name": "app-1"}}]}
    mock_resp.text = json.dumps(payload)
    mock_resp.json.return_value = payload
    mock_client._request.return_value = mock_resp


@given(parsers.parse('the TFC API accepts an action for workspace "{ws_id}"'))
def _mock_action_accepted(mock_client, ws_id):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    payload = {"data": {"id": ws_id, "type": "workspaces", "attributes": {"locked": True}}}
    mock_resp.text = json.dumps(payload)
    mock_resp.json.return_value = payload
    mock_client._request.return_value = mock_resp


@given(parsers.parse('the TFC API returns a 404 error for "{endpoint}"'))
def _mock_404_error(mock_client, endpoint):
    from terrapyne.core.exceptions import TFCNotFoundError

    mock_client._request.side_effect = TFCNotFoundError(
        "TFC API Error: 404 - Not Found", status_code=404
    )


@when(parsers.parse('I run "{command}"'), target_fixture="result")
def _run_command(mock_client, context_state, command):
    argv = command.split()[1:]  # strip 'tfc'
    detected_org = context_state.get("org")

    def _capture_request(method, path, params=None, json_data=None):
        context_state["captured_request"] = {
            "method": method,
            "path": path,
            "params": params,
            "json_data": json_data,
        }
        return mock_client._request.return_value

    def _mock_get_client(ctx, organization=None, host="app.terraform.io"):
        context_state["captured_host"] = host
        mock_enter = MagicMock()
        mock_enter.__enter__.return_value = mock_client
        return mock_enter

    if not mock_client._request.side_effect:
        mock_client._request.side_effect = _capture_request

    with (
        patch("terrapyne.cli.api_cmd.get_client", side_effect=_mock_get_client),
        patch(
            "terrapyne.cli.api_cmd.validate_context",
            return_value=(detected_org or "default-org", None),
        ),
    ):
        return runner.invoke(app, argv)


@given(parsers.parse('the TFC API accepts deletion of workspace "{ws_id}" returning empty body'))
def _mock_deletion_204(mock_client, ws_id):
    mock_resp = MagicMock()
    mock_resp.status_code = 204
    mock_resp.text = ""
    mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    mock_client._request.return_value = mock_resp


@then("the command succeeds")
def _command_succeeds(result):
    assert result.exit_code == 0, (
        f"Command failed: {result.output}\nStderr: {result.stderr if hasattr(result, 'stderr') else ''}"
    )


@then(
    parsers.parse(
        'the JSON output contains workspace attribute "{attr}" with value "{expected_value}"'
    )
)
def _check_json_attribute(result, attr, expected_value):
    raw_json = result.stdout if hasattr(result, "stdout") and result.stdout else result.output
    data = json.loads(raw_json)
    assert data["data"]["attributes"][attr] == expected_value


@then(parsers.parse('the request was sent to "{expected_path}"'))
def _check_request_path(context_state, expected_path):
    assert context_state["captured_request"]["path"] == expected_path


@then(parsers.parse('the request was sent to host "{expected_host}"'))
def _check_request_host(context_state, expected_host):
    assert context_state.get("captured_host") == expected_host


@then(parsers.parse('the request method was "{expected_method}"'))
def _check_request_method(context_state, expected_method):
    assert context_state["captured_request"]["method"] == expected_method


@then(parsers.parse('the request payload contained "{key}" with "{val}"'))
def _check_request_payload(context_state, key, val):
    payload = context_state["captured_request"]["json_data"]
    assert payload.get(key) == val


@then(parsers.parse('the request query params contained "{key}" with {val:d}'))
def _check_request_params_int(context_state, key, val):
    params = context_state["captured_request"]["params"]
    assert params.get(key) == val


@then(parsers.parse('the request query params contained "{key}" with "{val}"'))
def _check_request_params_str(context_state, key, val):
    params = context_state["captured_request"]["params"]
    assert params.get(key) == val


@then("the command exits with code 1")
def _command_fails(result):
    assert result.exit_code != 0


@then("stderr indicates the resource was not found")
def _check_stderr_404(result):
    # Output or error_console includes not found or 404
    output = result.output
    assert "404" in output or "Not Found" in output or "not found" in output.lower()


@then(parsers.parse('stderr contains an advisory hint recommending "{expected_cmd}"'))
def _check_stderr_advisory_hint(result, expected_cmd):
    stderr_text = result.stderr if hasattr(result, "stderr") and result.stderr else result.output
    assert "hint:" in stderr_text
    assert expected_cmd in stderr_text


@then("stderr does not contain an advisory hint")
def _check_stderr_no_hint(result):
    stderr_text = result.stderr if hasattr(result, "stderr") and result.stderr else ""
    assert "hint:" not in stderr_text
