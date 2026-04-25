"""BDD steps for --raw flag in state outputs command."""

import json
import re
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app

runner = CliRunner()

# Path to the feature file
FEATURE_FILE = "../features/state_raw_output.feature"


@scenario(FEATURE_FILE, "--raw returns unquoted string value")
def test_state_raw_string_value():
    """--raw returns unquoted string value."""


@scenario(FEATURE_FILE, "--raw with non-string value returns JSON representation")
def test_state_raw_json_value():
    """--raw with non-string value returns JSON representation."""


@scenario(FEATURE_FILE, "--raw with missing key exits non-zero")
def test_state_raw_missing_key():
    """--raw with missing key exits non-zero."""


# ============================================================================
# Given Steps
# ============================================================================


@given(parsers.parse('a workspace with output "{name}" = "{value}"'), target_fixture="mock_output")
def workspace_with_output(name, value):
    """Mock a workspace with a single string output."""
    mock_output = MagicMock()
    mock_output.name = name
    mock_output.value = value
    mock_output.type = "string"
    mock_output.sensitive = False
    return mock_output


@given(
    parsers.parse('a workspace with output "{name}" = {json_value}'), target_fixture="mock_output"
)
def workspace_with_json_output(name, json_value):
    """Mock a workspace with a complex output (list/dict)."""
    mock_output = MagicMock()
    mock_output.name = name
    mock_output.value = json.loads(json_value)
    mock_output.type = "map"
    mock_output.sensitive = False
    return mock_output


@given(parsers.parse('a workspace with no output named "{name}"'), target_fixture="mock_output")
def workspace_without_output(name):
    """Mock a workspace with no matching output."""
    return None


# ============================================================================
# When Steps
# ============================================================================


@when(parsers.parse("I run tfc state outputs {name} --raw"), target_fixture="cli_result")
def run_state_outputs_raw(name, mock_output):
    """Run the command with --raw flag."""
    with patch("terrapyne.api.client.TFCClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock workspace and state version resolution
        mock_ws = MagicMock()
        mock_ws.id = "ws-123"
        mock_client.workspaces.get.return_value = mock_ws

        mock_sv = MagicMock()
        mock_sv.id = "sv-xyz"
        mock_client.state_versions.get_current.return_value = mock_sv

        # Mock outputs
        if mock_output:
            mock_client.state_versions.list_outputs.return_value = [mock_output]
        else:
            mock_client.state_versions.list_outputs.return_value = []

        # PROVIDE WORKSPACE AS TARGET ARGUMENT
        # Command: tfc state outputs <workspace> <name> --raw
        return runner.invoke(
            app, ["state", "outputs", "my-ws", name, "--raw", "--organization", "test-org"]
        )


# ============================================================================
# Then Steps
# ============================================================================


@then(parsers.parse("stdout is exactly {expected}"))
def stdout_exact(cli_result, expected):
    # Remove trailing newline if present for comparison
    actual = cli_result.stdout.rstrip("\n")
    expected_val = expected.strip('"')
    assert actual == expected_val, f"Expected '{expected_val}', got '{actual}'"


@then("there is no table formatting")
def no_table_formatting(cli_result):
    assert "───" not in cli_result.stdout
    assert "Outputs for" not in cli_result.stdout


@then("there are no ANSI escape codes")
def no_ansi_codes(cli_result):
    ansi_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    assert not re.search(ansi_pattern, cli_result.stdout), "Output contains ANSI escape codes"


@then("stdout contains the JSON value")
def stdout_contains_json(cli_result):
    # Try to parse the output as JSON to verify it's valid JSON
    try:
        json.loads(cli_result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Output is not valid JSON: {cli_result.stdout}")


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(cli_result, code):
    assert cli_result.exit_code == code, (
        f"Expected exit code {code}, got {cli_result.exit_code}. Output: {cli_result.stdout}"
    )


@then(parsers.parse("stderr contains {text}"))
def stderr_contains(cli_result, text):
    expected = text.strip('"')
    assert expected in cli_result.stdout or expected in cli_result.stderr, (
        f"Expected '{expected}' in stderr, got: {cli_result.stderr}\nStdout: {cli_result.stdout}"
    )
