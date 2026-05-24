"""BDD steps for stdout/stderr separation contract.

Verifies that error/warning messages go to stderr, not stdout,
so that `tfc <cmd> --format json 2>/dev/null` always produces valid JSON.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.core.exceptions import TFCAPIError
from terrapyne.models.workspace import Workspace

runner = CliRunner()


@scenario(
    "../features/stdout_stderr_separation.feature",
    "A successful read command writes JSON to stdout only",
)
def test_successful_read_json_stdout_only():
    pass


@scenario(
    "../features/stdout_stderr_separation.feature",
    "A failing read command emits error text to stderr",
)
def test_failing_read_error_to_stderr():
    pass


@scenario(
    "../features/stdout_stderr_separation.feature",
    "Progress messages do not contaminate JSON output",
)
def test_progress_does_not_contaminate_json():
    pass


# --- Givens ---


@given("a command that supports --format json", target_fixture="mock_client")
def command_supports_json():
    m = MagicMock()
    m.workspaces.list.return_value = (
        iter(
            [
                Workspace.model_construct(
                    id="ws-abc",
                    name="my-app-dev",
                    terraform_version="1.9.0",
                    created_at=None,
                    updated_at=None,
                    auto_apply=False,
                    execution_mode="remote",
                    locked=False,
                    tag_names=[],
                    project_id=None,
                )
            ]
        ),
        1,
    )
    return m


@given("an organization name that does not exist", target_fixture="mock_client")
def org_does_not_exist():
    m = MagicMock()
    m.workspaces.list.side_effect = TFCAPIError(
        message="Organization 'ghost' not found",
        status_code=404,
        response={"errors": [{"title": "not found", "detail": "Organization not found"}]},
    )
    return m


@given(
    "a command that prints progress hints in TTY mode",
    target_fixture="mock_client",
)
def command_with_progress():
    m = MagicMock()
    m.workspaces.list.return_value = (
        iter(
            [
                Workspace.model_construct(
                    id="ws-abc",
                    name="my-app-dev",
                    terraform_version="1.9.0",
                    created_at=None,
                    updated_at=None,
                    auto_apply=False,
                    execution_mode="remote",
                    locked=False,
                    tag_names=[],
                    project_id=None,
                )
            ]
        ),
        1,
    )
    return m


# --- Whens ---


@when("the command runs successfully", target_fixture="cli_result")
def run_successful_command(mock_client):
    with (
        patch("terrapyne.cli.workspace_cmd.resolve_organization", return_value="test-org"),
        patch("terrapyne.cli.workspace_cmd.get_client") as gc,
    ):
        gc.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["workspace", "list", "-o", "test-org", "--format", "json"])


@when(
    'I run "tfc workspace list -o ghost --format json"',
    target_fixture="cli_result",
)
def run_failing_command(mock_client):
    with (
        patch("terrapyne.cli.workspace_cmd.resolve_organization", return_value="ghost"),
        patch("terrapyne.cli.workspace_cmd.get_client") as gc,
    ):
        gc.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["workspace", "list", "-o", "ghost", "--format", "json"])


@when(
    "stdout is redirected to a file and --format json is used",
    target_fixture="cli_result",
)
def run_with_stdout_redirected(mock_client):
    with (
        patch("terrapyne.cli.workspace_cmd.resolve_organization", return_value="test-org"),
        patch("terrapyne.cli.workspace_cmd.get_client") as gc,
    ):
        gc.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["workspace", "list", "-o", "test-org", "--format", "json"])


# --- Thens ---


@then("stdout contains valid JSON")
def stdout_is_valid_json(cli_result):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.stdout}"
    data = json.loads(cli_result.stdout)
    assert data is not None


@then("stderr is empty or contains only progress messages")
def stderr_empty_or_progress(cli_result):
    stderr = cli_result.stderr
    if stderr.strip():
        with pytest.raises(json.JSONDecodeError):
            json.loads(stderr)


@then("stdout is either empty or contains valid JSON")
def stdout_empty_or_valid_json(cli_result):
    stdout = cli_result.stdout.strip()
    if stdout:
        json.loads(stdout)


@then("stderr contains the human-readable error")
def stderr_has_error(cli_result):
    stderr = cli_result.stderr
    assert stderr.strip(), "Expected error message on stderr but got nothing"
    assert "error" in stderr.lower() or "not found" in stderr.lower()


@then("the exit code is non-zero")
def exit_code_nonzero(cli_result):
    assert cli_result.exit_code != 0


@then("the file contains exactly one valid JSON document")
def file_contains_one_json(cli_result):
    stdout = cli_result.stdout.strip()
    data = json.loads(stdout)
    assert data is not None
