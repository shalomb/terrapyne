"""BDD step definitions for workspace var subgroup commands."""

from unittest.mock import Mock, patch

from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.workspace import Workspace

scenarios("../features/workspace_var.feature")

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(name="my-app-dev", ws_id="ws-001"):
    ws = Mock(spec=Workspace)
    ws.id = ws_id
    ws.name = name
    return ws


def _make_var(key, value="val", var_id="var-001", category="terraform"):
    return WorkspaceVariable(
        id=var_id,
        key=key,
        value=value,
        category=category,
        hcl=False,
        sensitive=False,
        description=None,
    )


# ---------------------------------------------------------------------------
# Givens
# ---------------------------------------------------------------------------


@given('workspace "my-app-dev" has variables configured', target_fixture="mock_client")
def ws_has_variables():
    client = Mock()
    ws = _make_workspace()
    client.workspaces.get.return_value = ws
    client.workspaces.get_variables.return_value = [
        _make_var("region", "us-east-1"),
        _make_var("env", "production", var_id="var-002"),
    ]
    return client


@given('workspace "my-app-dev" exists with no existing variables', target_fixture="mock_client")
def ws_no_variables():
    client = Mock()
    ws = _make_workspace()
    client.workspaces.get.return_value = ws
    client.workspaces.get_variables.return_value = []
    client.workspaces.create_variable.return_value = _make_var("region", "us-east-1")
    return client


@given(
    'workspace "my-app-dev" has variable "region" set to "us-west-2"', target_fixture="mock_client"
)
def ws_has_region_variable():
    client = Mock()
    ws = _make_workspace()
    client.workspaces.get.return_value = ws
    client.workspaces.get_variables.return_value = [_make_var("region", "us-west-2")]
    return client


@given('workspace "my-app-dev" has variable "old-var" configured', target_fixture="mock_client")
def ws_has_old_var():
    client = Mock()
    ws = _make_workspace()
    client.workspaces.get.return_value = ws
    client.workspaces.get_variables.return_value = [_make_var("old-var", "some-value")]
    return client


@given('workspace "prod-app" has 2 variables', target_fixture="mock_client")
def prod_has_two_vars():
    client = Mock()
    prod_ws = _make_workspace("prod-app", "ws-prod")
    staging_ws = _make_workspace("staging-app", "ws-staging")

    def get_ws(name, org):
        return prod_ws if name == "prod-app" else staging_ws

    client.workspaces.get.side_effect = get_ws
    client.workspaces.get_variables.side_effect = lambda ws_id: (
        [_make_var("region", "us-east-1"), _make_var("env", "prod", var_id="var-002")]
        if ws_id == "ws-prod"
        else []
    )
    client.workspaces.create_variable.return_value = None
    return client


@given('workspace "staging-app" has no variables', target_fixture="mock_client")
def staging_no_vars(mock_client):
    """staging-app's empty variables already handled in prod_has_two_vars via side_effect."""
    return mock_client


# ---------------------------------------------------------------------------
# Whens
# ---------------------------------------------------------------------------


@when('I list variables for workspace "my-app-dev"', target_fixture="cli_result")
def list_vars(mock_client):
    with (
        patch("terrapyne.api.client.TFCClient") as c,
        patch("terrapyne.cli.context_helpers.validate_context") as v,
    ):
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["workspace", "var", "list", "my-app-dev", "-o", "test-org"])


@when(
    'I set variable "region" to "us-east-1" in workspace "my-app-dev"', target_fixture="cli_result"
)
def set_new_var(mock_client):
    with (
        patch("terrapyne.api.client.TFCClient") as c,
        patch("terrapyne.cli.context_helpers.validate_context") as v,
    ):
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(
            app,
            [
                "workspace",
                "var",
                "set",
                "my-app-dev",
                "--key",
                "region",
                "--value",
                "us-east-1",
                "-o",
                "test-org",
            ],
        )


@when(
    'I set variable "region" to "eu-west-1" in workspace "my-app-dev"', target_fixture="cli_result"
)
def set_existing_var(mock_client):
    with (
        patch("terrapyne.api.client.TFCClient") as c,
        patch("terrapyne.cli.context_helpers.validate_context") as v,
    ):
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(
            app,
            [
                "workspace",
                "var",
                "set",
                "my-app-dev",
                "--key",
                "region",
                "--value",
                "eu-west-1",
                "-o",
                "test-org",
            ],
        )


@when(
    'I remove variable "old-var" from workspace "my-app-dev" with --force',
    target_fixture="cli_result",
)
def remove_var_with_force(mock_client):
    with (
        patch("terrapyne.api.client.TFCClient") as c,
        patch("terrapyne.cli.context_helpers.validate_context") as v,
    ):
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(
            app,
            ["workspace", "var", "remove", "my-app-dev", "old-var", "-o", "test-org", "--force"],
        )


@when('I copy variables from "prod-app" to "staging-app"', target_fixture="cli_result")
def copy_vars(mock_client):
    with (
        patch("terrapyne.api.client.TFCClient") as c,
        patch("terrapyne.cli.context_helpers.validate_context") as v,
    ):
        v.return_value = ("test-org", None)
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(
            app,
            ["workspace", "var", "copy", "prod-app", "staging-app", "-o", "test-org"],
        )


# ---------------------------------------------------------------------------
# Thens
# ---------------------------------------------------------------------------


@then("I should see the variable listing")
def check_variable_listing(cli_result):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.stdout}"
    assert "region" in cli_result.stdout, (
        f"Expected variable key 'region' in output: {cli_result.stdout}"
    )
    assert "env" in cli_result.stdout, f"Expected variable key 'env' in output: {cli_result.stdout}"


@then("the variable should be created")
def check_var_created(cli_result):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.stdout}"


@then('output should confirm "Created variable: region"')
def check_created_output(cli_result):
    assert "Created variable: region" in cli_result.stdout


@then("the variable should be updated")
def check_var_updated(cli_result):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.stdout}"


@then('output should confirm "Updated variable: region"')
def check_updated_output(cli_result):
    assert "Updated variable: region" in cli_result.stdout


@then("the variable should be deleted")
def check_var_deleted(cli_result, mock_client):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.stdout}"
    mock_client.workspaces.delete_variable.assert_called_once()


@then('output should confirm "Removed variable: old-var"')
def check_removed_output(cli_result):
    assert "Removed variable: old-var" in cli_result.stdout


@then('2 variables should be created in "staging-app"')
def check_vars_copied(cli_result, mock_client):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.stdout}"
    assert mock_client.workspaces.create_variable.call_count == 2


@then("output should confirm variables were copied")
def check_copy_output(cli_result):
    assert "Done!" in cli_result.stdout


@then("exit code should be 0")
def exit_0(cli_result):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.stdout}"
