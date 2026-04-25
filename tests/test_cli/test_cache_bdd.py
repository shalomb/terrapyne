"""BDD tests for response caching."""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app

runner = CliRunner()


@scenario("../features/caching.feature", "Enable caching with --cache-ttl flag")
def test_cache_enabled():
    pass


@given('I run a command with the "--cache-ttl 60" flag', target_fixture="cache_context")
def cache_command_context():
    return {"args": ["--cache-ttl", "60"]}


@when("I request workspace details twice", target_fixture="cache_result")
def request_twice(cache_context, mock_httpx, mock_creds):
    # Setup mock response
    mock_httpx.return_value = MagicMock(
        status_code=200, text='{"data": {"id": "ws-123", "attributes": {"name": "my-ws"}}}'
    )
    mock_httpx.return_value.json.return_value = {
        "data": {"id": "ws-123", "attributes": {"name": "my-ws"}}
    }

    with patch("terrapyne.cli.utils.validate_context") as v:
        v.return_value = ("test-org", "my-ws")

        # First call
        runner.invoke(app, cache_context["args"] + ["workspace", "show", "my-ws", "-o", "test-org"])
        # Second call
        result = runner.invoke(
            app, cache_context["args"] + ["workspace", "show", "my-ws", "-o", "test-org"]
        )
        return result


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


@then("the second request should be served from the cache")
def check_cache_hit(mock_httpx):
    # Depending on how workspace show is implemented (Task 21),
    # it might make multiple requests (get workspace + get active runs count).
    # With caching, the second run should make FEWER requests than the first.
    # Total requests across both calls should be less than if caching was disabled.

    # Each workspace show makes 2 GET requests:
    # 1. /organizations/test-org/workspaces/my-ws?include=project,latest-run,latest-run.configuration-version
    # 2. /workspaces/ws-123/runs?status=...&limit=1

    # If caching works, the second call should make 0 requests.
    # Total requests = 2 (from first call) + 0 (from second call) = 2
    assert mock_httpx.call_count == 2


@then("the total number of API calls should be reduced")
def check_api_calls_reduced(mock_httpx):
    assert mock_httpx.call_count < 4  # 2 calls per workspace show * 2 shows = 4
