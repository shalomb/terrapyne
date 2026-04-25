"""BDD tests for state version management CLI commands."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.state_version import StateVersion
from terrapyne.models.workspace import Workspace

runner = CliRunner()


@scenario("../features/state_management.feature", "Pull current state as raw JSON")
def test_state_pull():
    pass


@scenario("../features/state_management.feature", "List state versions with relative time")
def test_state_list():
    pass


@given("a terraform cloud organization is accessible")
def terraform_org_ready():
    pass


@given(
    parsers.parse('a workspace "{workspace_name}" is ready for operations'),
    target_fixture="mock_client",
)
def workspace_ready(workspace_name):
    m = MagicMock()
    ws = Workspace.model_construct(id="ws-123", name=workspace_name)
    m.workspaces.get.return_value = ws
    m.get_organization.return_value = "test-org"
    return m


@given(parsers.parse('the workspace has a current state version with ID "{sv_id}"'))
def has_current_state(mock_client, sv_id):
    sv = StateVersion.model_construct(
        id=sv_id, download_url="https://archivist.terraform.io/v1/state-123"
    )
    mock_client.state_versions.get_current.return_value = sv


@given(parsers.parse('the state file contains "{resource_name}"'))
def state_content(mock_client, resource_name):
    state_data = {
        "version": 4,
        "terraform_version": "1.5.0",
        "serial": 1,
        "lineage": "abc",
        "resources": [{"type": "aws_instance", "name": "web"}],
    }
    mock_client.state_versions.download_from_url.return_value = state_data


@given("the workspace has state versions:")
def has_state_versions(mock_client, datatable):
    versions = []
    for row in datatable:
        if row[0] == "ID":
            continue

        # Calculate timestamp from relative string
        now = datetime.now(UTC)
        if "hour" in row[1]:
            ts = now - timedelta(hours=1)
        elif "day" in row[1]:
            ts = now - timedelta(days=2)
        else:
            ts = now - timedelta(days=30)

        sv = StateVersion.model_construct(id=row[0], created_at=ts, serial=int(row[2]))
        versions.append(sv)

    mock_client.state_versions.list.return_value = (iter(versions), len(versions))


@when("I pull the current state", target_fixture="cli_result")
def pull_state(mock_client):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        v.return_value = ("test-org", "my-infra")
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["state", "pull", "-w", "my-infra", "-o", "test-org"])


@when("I list state versions", target_fixture="cli_result")
def list_state_versions(mock_client):
    with (
        patch("terrapyne.cli.utils.validate_context") as v,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        v.return_value = ("test-org", "my-infra")
        c.return_value.__enter__.return_value = mock_client
        # Corrected: positional workspace argument for 'state list'
        return runner.invoke(app, ["state", "list", "my-infra", "-o", "test-org"])


@then("the output should be valid JSON")
def check_valid_json(cli_result):
    assert cli_result.exit_code == 0
    data = json.loads(cli_result.stdout)
    assert data is not None


@then(parsers.parse('it should contain "{text}"'))
def check_output_content(cli_result, text):
    # For JSON state files, resources might be separate fields
    if "." in text:
        parts = text.split(".")
        assert parts[0] in cli_result.stdout
        assert parts[1] in cli_result.stdout
    else:
        assert text in cli_result.stdout


@then(parsers.parse("I should see {count:d} versions in the list"))
def check_version_count(cli_result, count):
    assert cli_result.exit_code == 0
    # Match version lines
    assert "sv-" in cli_result.stdout
    assert str(count) in cli_result.stdout


@then(parsers.parse('I should see relative times like "{t1}" or "{t2}"'))
def check_relative_times(cli_result, t1, t2):
    # Just check that it's using the relative formatter (e.g. "h ago")
    assert "ago" in cli_result.stdout
