"""BDD tests for debug mode and API tracing."""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app

runner = CliRunner()


@scenario("../features/debug_mode.feature", "Enable API tracing with --debug flag")
def test_debug_mode_enabled():
    pass


@scenario("../features/debug_mode.feature", "Debug mode handles API errors gracefully")
def test_debug_mode_errors():
    pass


@given('I run a command with the "--debug" flag', target_fixture="debug_context")
def debug_command_context():
    return {"args": ["--debug"]}


@given("the API request will fail with a 404 error")
def api_fails_404(mock_httpx):
    mock_httpx.return_value = MagicMock(
        status_code=404, text='{"errors": [{"status": "404", "title": "not found"}]}'
    )


@when("the command makes an API request to Terraform Cloud", target_fixture="cli_result")
def make_api_request(debug_context, mock_httpx, mock_creds):
    # Setup mock response
    mock_httpx.return_value = MagicMock(
        status_code=200, text='{"data": {"id": "ws-123", "attributes": {"name": "my-ws"}}}'
    )
    mock_httpx.return_value.json.return_value = {
        "data": {"id": "ws-123", "attributes": {"name": "my-ws"}}
    }

    with patch("terrapyne.cli.utils.validate_context") as v:
        v.return_value = ("test-org", "my-ws")
        # Run the command. Typer will call main() which calls setup_logging()
        return runner.invoke(
            app, debug_context["args"] + ["workspace", "show", "my-ws", "-o", "test-org"]
        )


@when("I execute the command", target_fixture="cli_result")
def execute_command(debug_context, mock_httpx, mock_creds):
    # httpx mock should already be configured by 'given' step
    with patch("terrapyne.cli.utils.validate_context") as v:
        v.return_value = ("test-org", "my-ws")
        return runner.invoke(
            app, debug_context["args"] + ["workspace", "show", "my-ws", "-o", "test-org"]
        )


@pytest.fixture
def mock_httpx():
    with patch("httpx.Client.request") as m:
        yield m


@pytest.fixture
def mock_creds():
    with patch("terrapyne.core.credentials.TerraformCredentials.load") as m:
        m.return_value = MagicMock()
        m.return_value.get_headers.return_value = {"Authorization": "Bearer XXX"}
        yield m


@then("the request details should be printed to stderr")
def check_request_in_stderr(cli_result):
    # We check both stdout and stderr since CliRunner might mix them depending on config
    # Actually CliRunner.stderr should have it if we used StreamHandler()
    output = cli_result.stdout + cli_result.stderr
    assert "API Request" in output
    assert "GET" in output


@then("the response details should be printed to stderr")
def check_response_in_stderr(cli_result):
    output = cli_result.stdout + cli_result.stderr
    assert "API Response" in output
    assert "200" in output or "404" in output


@then("the error body should be printed to stderr")
def check_error_in_stderr(cli_result):
    output = cli_result.stdout + cli_result.stderr
    assert "Error Body" in output
    assert "not found" in output


@then("the command should exit with an error code")
def check_exit_error(cli_result):
    assert cli_result.exit_code != 0
