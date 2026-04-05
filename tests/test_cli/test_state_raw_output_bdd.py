"""BDD steps for --raw flag in state outputs command."""
import json
import re
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.state_version import StateVersionOutput
from terrapyne.models.workspace import Workspace

runner = CliRunner()


@scenario("../features/state_raw_output.feature", "--raw returns unquoted string value")
def test_state_raw_string_value():
    pass


@scenario("../features/state_raw_output.feature", "--raw with non-string value returns JSON representation")
def test_state_raw_json_value():
    pass


@scenario("../features/state_raw_output.feature", "--raw with missing key exits non-zero")
def test_state_raw_missing_key():
    pass


@given(
    parsers.parse('a workspace with output "{key}" = "{value}"'),
    target_fixture="mock_client_with_output",
)
def workspace_with_string_output(key, value):
    m = MagicMock()
    m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
    m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
    m.state_versions.list_outputs.return_value = [
        StateVersionOutput(name=key, value=value, type="string", sensitive=False)
    ]
    return m


@given(
    parsers.parse('a workspace with output "{key}" = {json_value}'),
    target_fixture="mock_client_with_output",
)
def workspace_with_json_output(key, json_value):
    m = MagicMock()
    m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
    m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
    parsed_value = json.loads(json_value)
    m.state_versions.list_outputs.return_value = [
        StateVersionOutput(name=key, value=parsed_value, type="object", sensitive=False)
    ]
    return m


@given(
    parsers.parse('a workspace with no output named "{key}"'),
    target_fixture="mock_client_with_output",
)
def workspace_with_no_output(key):
    m = MagicMock()
    m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
    m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
    m.state_versions.list_outputs.return_value = []
    return m


@when(
    parsers.parse("I run tfc state outputs {key} --raw"),
    target_fixture="cli_result",
)
def run_state_outputs_raw(mock_client_with_output, key):
    with patch("terrapyne.cli.state_cmd.TFCClient") as c:
        c.return_value.__enter__.return_value = mock_client_with_output
        return runner.invoke(app, ["state", "outputs", key, "-w", "test-ws", "-o", "test-org", "--raw"])


@then(parsers.parse("stdout is exactly {expected}"))
def stdout_exact(cli_result, expected):
    # Remove trailing newline if present for comparison
    actual = cli_result.stdout.rstrip("\n")
    expected_val = expected.strip('"')
    assert actual == expected_val, f"Expected '{expected_val}', got '{actual}'"


@then("there is no table formatting")
def no_table_formatting(cli_result):
    # Check that output doesn't contain table box-drawing characters or pipes
    assert "│" not in cli_result.stdout, "Output contains table formatting"
    assert "─" not in cli_result.stdout, "Output contains table formatting"
    assert "┬" not in cli_result.stdout, "Output contains table formatting"
    assert "┼" not in cli_result.stdout, "Output contains table formatting"


@then("there are no ANSI escape codes")
def no_ansi_codes(cli_result):
    # ANSI escape sequences start with \033[ or \x1b[
    ansi_pattern = r"\033\[|\x1b\["
    assert not re.search(ansi_pattern, cli_result.stdout), "Output contains ANSI escape codes"


@then("stdout contains the JSON value")
def stdout_contains_json(cli_result):
    # Try to parse the output as JSON to verify it's valid JSON
    try:
        json.loads(cli_result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Output is not valid JSON: {cli_result.stdout}")


@then(parsers.parse("the exit code is {code:d}"))
def exit_code_is(cli_result, code):
    assert cli_result.exit_code == code, f"Expected exit code {code}, got {cli_result.exit_code}. Output: {cli_result.stdout}"


@then(parsers.parse("stderr contains {text}"))
def stderr_contains(cli_result, text):
    expected = text.strip('"')
    assert expected in cli_result.stderr, f"Expected '{expected}' in stderr, got: {cli_result.stderr}\nStdout: {cli_result.stdout}"
