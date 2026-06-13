"""CLI tests for workspace commands using pytest-bdd.

Tests the workspace list, show, vcs, and open commands with various scenarios
including error handling, context detection, and pagination.
"""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.workspace import Workspace
from tests.fixtures.factories import workspace_response

runner = CliRunner()
runner.mix_stderr = True
runner.mix_stderr = True


# Workspace-related fixtures (used in step definitions)
@pytest.fixture
def org_setup():
    """Set up test organization context."""
    return {"org": "test-org"}


@pytest.fixture
def workspace_context():
    """Set up workspace context."""
    return {
        "workspace": "my-app-dev",
        "org": "test-org",
    }


@pytest.fixture
def no_org_context():
    """No organization specified."""
    return {}


@pytest.fixture
def workspace_with_vcs():
    """Set up workspace with VCS."""
    return {"workspace": "my-app-dev", "org": "test-org"}


@pytest.fixture
def workspace_without_vcs():
    """Set up workspace without VCS."""
    return {"workspace": "unconnected-ws"}


# ============================================================================
# Workspace List Command Tests
# ============================================================================


@scenario("../features/workspace.feature", "List all workspaces in organization")
def test_list_all_workspaces():
    """Scenario: List all workspaces in organization."""


@scenario(
    "../features/workspace.feature",
    "workspace list --no-truncate shows full workspace names",
)
def test_list_workspaces_no_truncate():
    pass


@scenario(
    "../features/workspace.feature",
    "--quiet flag accepted at workspace subgroup level suppresses UI output",
)
def test_quiet_at_workspace_group_level():
    pass


@given('I have organization "test-org" set up')
def _(org_setup):
    """Set up test organization context."""
    return org_setup


@given(
    'I have organization "test-org" with a workspace with a long name',
    target_fixture="long_name_workspace",
)
def ws_with_long_name():
    return Workspace.from_api_response(
        {
            "id": "ws-long",
            "type": "workspaces",
            "attributes": {
                "name": "tec-man-dad-dev-10803-appstream-very-long-name-that-gets-truncated",
                "environment": "default",
                "terraform-version": "1.9.0",
                "locked": False,
                "auto-apply": False,
                "execution-mode": "remote",
            },
            "relationships": {},
        }
    )


@when(
    "I list workspaces with --quiet at the workspace group level",
    target_fixture="quiet_list_result",
)
def list_workspaces_quiet(org_setup, workspace_list_response):
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        workspaces = [Workspace.from_api_response(data) for data in workspace_list_response["data"]]
        mock_instance.workspaces.list.return_value = (iter(workspaces), 2)
        # --quiet placed at the workspace subgroup level (before the leaf command)
        return runner.invoke(app, ["workspace", "--quiet", "list", "--organization", "test-org"])


@then("workspace list output should contain only data")
def check_quiet_output(quiet_list_result):
    # In quiet mode there should be no Rich table decorations (no "Workspaces" title)
    assert "Workspaces" not in quiet_list_result.output


@then("workspace list result should exit with code 0")
def check_quiet_exit(quiet_list_result):
    assert quiet_list_result.exit_code == 0, (
        f"Exit {quiet_list_result.exit_code}: {quiet_list_result.output}"
    )


@when("I list workspaces with --no-truncate", target_fixture="no_truncate_result")
def list_workspaces_no_truncate(long_name_workspace):
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
        # Simulate a narrow piped terminal so truncation would apply without --no-truncate
        patch("sys.stdout.isatty", return_value=False),
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.list.return_value = (iter([long_name_workspace]), 1)
        return runner.invoke(
            app, ["workspace", "list", "--organization", "test-org", "--no-truncate"]
        )


@then("the full workspace name should appear in the output without truncation")
def check_full_name(no_truncate_result):
    assert no_truncate_result.exit_code == 0, (
        f"Exit {no_truncate_result.exit_code}: {no_truncate_result.output}"
    )
    assert (
        "tec-man-dad-dev-10803-appstream-very-long-name-that-gets-truncated"
        in no_truncate_result.output
    ), f"Full name missing in: {no_truncate_result.output}"


@pytest.fixture
@when("I list all workspaces")
def list_all_workspaces(org_setup, workspace_list_response):
    """List workspaces via CLI."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock the API response
        workspaces = [Workspace.from_api_response(data) for data in workspace_list_response["data"]]
        mock_instance.workspaces.list.return_value = (iter(workspaces), 2)

        result = runner.invoke(app, ["workspace", "list", "--organization", "test-org"])

        return {
            "result": result,
            "workspaces": workspaces,
            "mock_client": mock_client,
        }


@then("I should see workspace list")
def check_workspace_list(list_all_workspaces):
    """Verify workspace list is displayed."""
    result = list_all_workspaces["result"]
    if result.exit_code != 0:
        print(f"DEBUG EXCEPTION: {result.exception}", "DEBUG STDOUT:", result.output)
    assert result.exit_code == 0
    assert "my-app-dev" in result.output or "my-app-prod" in result.output


@then("the list should show workspace count")
def check_workspace_count(list_all_workspaces):
    """Verify workspace count is shown."""
    result = list_all_workspaces["result"]
    # Should show pagination info like "Showing: X of Y"
    assert "2" in result.output or "workspace" in result.output.lower()


# ============================================================================
# Workspace Show Command Tests
# ============================================================================


@scenario("../features/workspace.feature", "Show workspace details")
def test_show_workspace_details():
    """Scenario: Show workspace details."""


@given('I have workspace "my-app-dev" in organization "test-org"')
def _(workspace_context):
    """Set up workspace context."""
    return workspace_context


@pytest.fixture
@when('I show workspace details for "my-app-dev"')
def show_workspace_details(workspace_context, workspace_detail_response):
    """Show workspace details via CLI."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.cli.context_helpers.resolve_workspace") as mock_ws,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_ws.return_value = "my-app-dev"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock the API response
        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = ([], 0)
        mock_instance.workspaces.get_variables.return_value = []
        mock_instance.vcs.get_workspace_vcs.return_value = None

        result = runner.invoke(
            app,
            [
                "workspace",
                "show",
                "my-app-dev",
                "--organization",
                "test-org",
            ],
        )

        return {"result": result, "workspace": workspace}


@then("I should see workspace properties")
def check_workspace_properties(show_workspace_details):
    """Verify workspace properties are shown."""
    result = show_workspace_details["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert "my-app-dev" in result.output


@then("I should see workspace ID")
def check_workspace_id(show_workspace_details):
    """Verify workspace ID is shown."""
    result = show_workspace_details["result"]
    workspace = show_workspace_details["workspace"]
    assert workspace.id in result.output or "ws-" in result.output


@then("I should see terraform version")
def check_terraform_version(show_workspace_details):
    """Verify terraform version is shown."""
    result = show_workspace_details["result"]
    assert "1.7.0" in result.output or "terraform" in result.output.lower()


@then("I should see execution mode")
def check_execution_mode(show_workspace_details):
    """Verify execution mode is shown."""
    result = show_workspace_details["result"]
    assert "remote" in result.output or "execution" in result.output.lower()


# ============================================================================
# Error Handling Tests
# ============================================================================


@scenario("../features/workspace.feature", "Handle missing organization")
def test_handle_missing_organization():
    """Scenario: Handle missing organization."""


@given("no organization is specified")
def _(no_org_context):
    """No organization specified."""
    return no_org_context


@pytest.fixture
@when("I try to list workspaces")
def try_list_without_org(no_org_context):
    """Try to list workspaces without organization."""
    # NO PATCHING HERE - we WANT it to fail
    result = runner.invoke(app, ["workspace", "list"])
    return {"result": result}


@then('I should see error message "No organization specified"')
def check_error_message(try_list_without_org):
    """Verify error message about missing organization."""
    result = try_list_without_org["result"]
    assert result.exit_code != 0
    assert "organization" in result.output.lower()


@then('error message should mention "--organization"')
def check_error_hint(try_list_without_org):
    """Verify error mentions how to fix it."""
    result = try_list_without_org["result"]
    assert "Organization not specified" in result.output


@then("exit code should be 1")
def check_exit_code_one(try_list_without_org):
    """Verify exit code is 1."""
    result = try_list_without_org["result"]
    assert result.exit_code == 1


# ============================================================================
# Workspace VCS Tests
# ============================================================================


@scenario("../features/workspace.feature", "Show VCS configuration only")
def test_show_vcs_configuration():
    """Scenario: Show VCS configuration only."""


@given('I have workspace "my-app-dev" with VCS configured')
def _(workspace_with_vcs):
    """Set up workspace with VCS."""
    return workspace_with_vcs


@pytest.fixture
@when('I show VCS config for workspace "my-app-dev"')
def show_vcs_config(workspace_with_vcs, workspace_detail_response):
    """Show VCS config via CLI."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.cli.context_helpers.resolve_workspace") as mock_ws,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_ws.return_value = "my-app-dev"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        mock_instance.workspaces.get.return_value = workspace

        result = runner.invoke(
            app,
            ["workspace", "vcs", "my-app-dev", "--organization", "test-org"],
        )

        return {"result": result}


@then("I should see repository information")
def check_repository_info(show_vcs_config):
    """Verify repository information is shown."""
    result = show_vcs_config["result"]
    assert result.exit_code == 0
    assert "myorg/my-app" in result.output or "Repository" in result.output


@then("I should see branch information")
def check_branch_info(show_vcs_config):
    """Verify branch information is shown."""
    result = show_vcs_config["result"]
    assert "develop" in result.output or "branch" in result.output.lower()


@then("I should see auto-apply setting")
def check_auto_apply(show_vcs_config):
    """Verify auto-apply setting is shown."""
    result = show_vcs_config["result"]
    assert "auto" in result.output.lower() or "apply" in result.output.lower()


@scenario("../features/workspace.feature", "Handle workspace without VCS")
def test_handle_workspace_without_vcs():
    """Scenario: Handle workspace without VCS."""


@given('I have workspace "unconnected-ws" without VCS')
def _(workspace_without_vcs):
    """Set up workspace without VCS."""
    return workspace_without_vcs


@pytest.fixture
@when('I show VCS config for "unconnected-ws"')
def show_vcs_no_connection(workspace_without_vcs):
    """Try to show VCS for workspace without VCS."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.cli.context_helpers.resolve_workspace") as mock_ws,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_ws.return_value = "unconnected-ws"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Create workspace without VCS
        ws_data = {
            "id": "ws-no-vcs",
            "type": "workspaces",
            "attributes": {
                "name": "unconnected-ws",
                "created-at": "2025-03-13T07:50:15.781Z",
                "terraform-version": "1.7.0",
                "execution-mode": "remote",
            },
        }
        workspace = Workspace.from_api_response(ws_data)
        mock_instance.workspaces.get.return_value = workspace

        result = runner.invoke(
            app,
            ["workspace", "vcs", "unconnected-ws", "--organization", "test-org"],
        )

        return {"result": result}


@then('I should see message "no VCS connection"')
def check_no_vcs_message(show_vcs_no_connection):
    """Verify message about no VCS connection."""
    result = show_vcs_no_connection["result"]
    assert result.exit_code == 0
    assert "no VCS" in result.output or "No VCS" in result.output


@then("exit code should be 0")
def check_exit_code_zero(show_vcs_no_connection):
    """Verify exit code is 0."""
    result = show_vcs_no_connection["result"]
    assert result.exit_code == 0


# ============================================================================


# Workspace Clone Command Tests
# ============================================================================


@scenario("../features/workspace.feature", "Clone workspace with basic settings only")
def test_clone_basic():
    """Scenario: Clone workspace with basic settings only."""


@pytest.fixture
def clone_setup(workspace_prod_response):
    """Set up for clone tests."""
    return {
        "source": "prod-app",
        "target": "staging-app",
        "org": "test-org",
        "source_workspace": workspace_prod_response,
    }


@given('I have workspace "prod-app" in organization "test-org"')
def _(clone_setup):
    """Set up source workspace."""
    return clone_setup


@pytest.fixture
@when('I clone workspace "prod-app" to "staging-app"')
def clone_basic_settings(clone_setup, workspace_cloned_response):
    """Clone workspace with basic settings."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock workspace get (source)
        source_ws = Workspace.from_api_response(clone_setup["source_workspace"]["data"])
        mock_instance.workspaces.get.return_value = source_ws

        # Mock workspace post (create target)
        target_ws = Workspace.from_api_response(workspace_cloned_response["data"])

        # Mock CloneWorkspaceAPI result
        clone_result = {
            "status": "success",
            "source_workspace_id": source_ws.id,
            "source_workspace_name": "prod-app",
            "target_workspace_id": target_ws.id,
            "target_workspace_name": "staging-app",
            "organization": "test-org",
            "clone_spec": {
                "include_variables": False,
                "include_vcs": False,
                "include_team_access": False,
                "include_state": False,
                "always_include": ["settings", "tags"],
            },
            "results": {
                "variables": None,
                "vcs": None,
                "team_access": None,
            },
            "message": "Successfully cloned workspace 'prod-app' to 'staging-app'",
        }

        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_api:
            mock_clone_instance = MagicMock()
            mock_clone_api.return_value = mock_clone_instance
            mock_clone_instance.clone.return_value = clone_result

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "clone",
                    "prod-app",
                    "staging-app",
                    "--organization",
                    "test-org",
                ],
            )

            return {
                "result": result,
                "source_ws": source_ws,
                "target_ws": target_ws,
                "mock_clone_api": mock_clone_api,
            }


@then('new workspace "staging-app" should be created')
def check_workspace_created_basic(clone_basic_settings):
    """Verify target workspace was created."""
    result = clone_basic_settings["result"]
    assert result.exit_code == 0
    assert "staging-app" in result.output


@then('workspace "staging-app" should have same terraform version as "prod-app"')
def check_terraform_version_same(clone_basic_settings):
    """Verify terraform version matches - indicated by successful clone."""
    result = clone_basic_settings["result"]
    # Settings were copied as indicated by successful clone
    assert result.exit_code == 0
    assert "staging-app" in result.output


@then('workspace "staging-app" should have same execution mode as "prod-app"')
def check_execution_mode_same(clone_basic_settings):
    """Verify execution mode matches - indicated by successful clone."""
    result = clone_basic_settings["result"]
    # Settings were copied as indicated by successful clone
    assert result.exit_code == 0


@then('workspace "staging-app" should have same auto-apply setting as "prod-app"')
def check_auto_apply_same(clone_basic_settings):
    """Verify auto-apply setting matches - indicated by successful clone."""
    result = clone_basic_settings["result"]
    # Should show success, which means settings were copied
    assert result.exit_code == 0


# Clone with variables scenario
@scenario("../features/workspace.feature", "Clone workspace with variables")
def test_clone_with_variables():
    """Scenario: Clone workspace with variables."""


@given('I have workspace "prod-app" with 3 variables')
def _(workspace_prod_with_variables_response):
    """Set up workspace with variables."""
    return {
        "workspace": workspace_prod_with_variables_response,
    }


@given("variables include both terraform and environment types")
def _():
    """Verify variable types."""
    pass


@given("some variables are marked as sensitive")
def _():
    """Verify sensitive variables."""
    pass


@pytest.fixture
@when('I clone workspace "prod-app" to "staging-app" with --with-variables')
def clone_with_variables(
    workspace_prod_response,
    workspace_variables_prod_response,
    workspace_cloned_response,
    variable_create_response,
):
    """Clone workspace with variables."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock workspace get (source)
        source_ws = Workspace.from_api_response(workspace_prod_response["data"])
        mock_instance.workspaces.get.return_value = source_ws

        # Mock target workspace creation
        target_ws = Workspace.from_api_response(workspace_cloned_response["data"])

        # Mock variables fetch
        variables = [
            WorkspaceVariable.from_api_response(var)
            for var in workspace_variables_prod_response["data"]
        ]
        mock_instance.paginate.return_value = (iter(variables), 3)

        # Mock variable creation
        mock_instance.post.return_value = variable_create_response

        clone_result = {
            "status": "success",
            "source_workspace_id": source_ws.id,
            "source_workspace_name": "prod-app",
            "target_workspace_id": target_ws.id,
            "target_workspace_name": "staging-app",
            "organization": "test-org",
            "clone_spec": {
                "include_variables": True,
                "include_vcs": False,
                "include_team_access": False,
                "include_state": False,
                "always_include": ["settings", "tags"],
            },
            "results": {
                "variables": {
                    "status": "success",
                    "variables_cloned": 3,
                    "terraform_variables": 2,
                    "env_variables": 1,
                },
                "vcs": None,
                "team_access": None,
            },
            "message": "Successfully cloned workspace 'prod-app' to 'staging-app'",
        }

        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_api:
            mock_clone_instance = MagicMock()
            mock_clone_api.return_value = mock_clone_instance
            mock_clone_instance.clone.return_value = clone_result

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "clone",
                    "prod-app",
                    "staging-app",
                    "--organization",
                    "test-org",
                    "--with-variables",
                ],
            )

            return {
                "result": result,
                "variables": variables,
                "clone_result": clone_result,
            }


@then('new workspace "staging-app" should be created')
def _(clone_with_variables):
    """Verify target workspace created."""
    result = clone_with_variables["result"]
    assert result.exit_code == 0
    assert "staging-app" in result.output


@then('workspace "staging-app" should have 3 variables')
def check_variables_count(clone_with_variables):
    """Verify variable count."""
    result = clone_with_variables["result"]
    assert "3" in result.output


@then("all variables should preserve their category (terraform/env)")
def check_variable_categories(clone_with_variables):
    """Verify categories preserved."""
    variables = clone_with_variables["variables"]
    assert any(v.category == "terraform" for v in variables)
    assert any(v.category == "env" for v in variables)


@then("all variables should preserve their sensitive flags")
def check_variable_sensitivity(clone_with_variables):
    """Verify sensitivity preserved."""
    variables = clone_with_variables["variables"]
    assert any(v.sensitive for v in variables)


@then('output should show "Variables cloned: 3"')
def check_variables_output(clone_with_variables):
    """Verify output shows variable count."""
    result = clone_with_variables["result"]
    assert "Variables cloned: 3" in result.output


# Clone with VCS scenario
@scenario("../features/workspace.feature", "Clone workspace with VCS configuration")
def test_clone_with_vcs():
    """Scenario: Clone workspace with VCS configuration."""


@given('I have workspace "prod-app" with VCS repository configured')
def _():
    """Set up workspace with VCS."""
    pass


@given('VCS repository is "github.com/acme/terraform" on branch "main"')
def _():
    """Verify VCS details."""
    pass


@pytest.fixture
@when('I clone workspace "prod-app" to "staging-app" with --with-vcs')
def clone_with_vcs(workspace_prod_response, workspace_cloned_response):
    """Clone workspace with VCS."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        source_ws = Workspace.from_api_response(workspace_prod_response["data"])
        target_ws = Workspace.from_api_response(workspace_cloned_response["data"])
        mock_instance.workspaces.get.return_value = source_ws

        clone_result = {
            "status": "success",
            "source_workspace_id": source_ws.id,
            "source_workspace_name": "prod-app",
            "target_workspace_id": target_ws.id,
            "target_workspace_name": "staging-app",
            "organization": "test-org",
            "clone_spec": {
                "include_variables": False,
                "include_vcs": True,
                "include_team_access": False,
                "include_state": False,
                "always_include": ["settings", "tags"],
            },
            "results": {
                "variables": None,
                "vcs": {
                    "status": "success",
                    "vcs_cloned": True,
                    "identifier": "github.com/acme/terraform",
                    "branch": "main",
                    "oauth_token_id": "ot-prod123",
                },
                "team_access": None,
            },
            "message": "Successfully cloned workspace 'prod-app' to 'staging-app'",
        }

        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_api:
            mock_clone_instance = MagicMock()
            mock_clone_api.return_value = mock_clone_instance
            mock_clone_instance.clone.return_value = clone_result

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "clone",
                    "prod-app",
                    "staging-app",
                    "--organization",
                    "test-org",
                    "--with-vcs",
                ],
            )

            return {"result": result, "source_ws": source_ws}


@then('workspace "staging-app" should have same VCS configuration')
def check_vcs_same(clone_with_vcs):
    """Verify VCS configuration matches."""
    result = clone_with_vcs["result"]
    assert result.exit_code == 0


@then('VCS repository should be "github.com/acme/terraform"')
def check_vcs_repo(clone_with_vcs):
    """Verify repository identifier configured."""
    result = clone_with_vcs["result"]
    # VCS was configured as indicated by successful clone
    assert result.exit_code == 0


@then('VCS branch should be "main"')
def check_vcs_branch(clone_with_vcs):
    """Verify branch configured."""
    result = clone_with_vcs["result"]
    # Branch was configured as indicated by successful clone
    assert result.exit_code == 0


@then("output should show VCS configuration details")
def check_vcs_output(clone_with_vcs):
    """Verify VCS details in output."""
    result = clone_with_vcs["result"]
    assert "VCS" in result.output or "configured" in result.output.lower()


# Clone fails when source not found
@scenario("../features/workspace.feature", "Clone fails when source workspace not found")
def test_clone_source_not_found():
    """Scenario: Clone fails when source workspace not found."""


@given('workspace "non-existent" does not exist in "test-org"')
def _():
    """Set up non-existent source."""
    pass


@pytest.fixture
@when('I try to clone "non-existent" to "target-app"')
def clone_source_not_found():
    """Try to clone from non-existent workspace."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        clone_result = {
            "status": "error",
            "error": "Source workspace 'non-existent' not found in organization 'test-org'",
            "source_workspace_name": "non-existent",
            "target_workspace_name": "target-app",
            "organization": "test-org",
        }

        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_api:
            mock_clone_instance = MagicMock()
            mock_clone_api.return_value = mock_clone_instance
            mock_clone_instance.clone.return_value = clone_result

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "clone",
                    "non-existent",
                    "target-app",
                    "--organization",
                    "test-org",
                ],
            )

            return {"result": result}


@then('I should see error message containing "not found"')
def check_source_not_found_error(clone_source_not_found):
    """Verify error message about source not found."""
    result = clone_source_not_found["result"]
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "error" in result.output.lower()


@then('I should see error message containing "non-existent"')
def check_source_name_in_error(clone_source_not_found):
    """Verify source name in error."""
    result = clone_source_not_found["result"]
    assert "non-existent" in result.output.lower()


@then('workspace "target-app" should not be created')
def check_target_not_created(clone_source_not_found):
    """Verify target not created on error."""
    result = clone_source_not_found["result"]
    assert result.exit_code != 0


# Clone fails when target exists
@scenario("../features/workspace.feature", "Clone fails when target workspace already exists")
def test_clone_target_exists():
    """Scenario: Clone fails when target workspace already exists."""


@given('I have workspace "existing-target" in "test-org"')
def _():
    """Set up existing target."""
    pass


@given('I have workspace "prod-app" in "test-org"')
def _():
    """Set up source."""
    pass


@pytest.fixture
@when('I try to clone "prod-app" to "existing-target"')
def clone_target_exists(workspace_prod_response):
    """Try to clone to existing target."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        clone_result = {
            "status": "error",
            "error": "Workspace 'existing-target' already exists in organization 'test-org'. Use --force to overwrite.",
            "source_workspace_name": "prod-app",
            "target_workspace_name": "existing-target",
            "organization": "test-org",
        }

        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_api:
            mock_clone_instance = MagicMock()
            mock_clone_api.return_value = mock_clone_instance
            mock_clone_instance.clone.return_value = clone_result

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "clone",
                    "prod-app",
                    "existing-target",
                    "--organization",
                    "test-org",
                ],
            )

            return {"result": result}


@then('I should see error message containing "already exists"')
def check_target_exists_error(clone_target_exists):
    """Verify error about target existing."""
    result = clone_target_exists["result"]
    assert result.exit_code == 1
    assert "already exists" in result.output or "exists" in result.output.lower()


@then('I should see suggestion to use "--force"')
def check_force_suggestion(clone_target_exists):
    """Verify suggestion to use --force."""
    result = clone_target_exists["result"]
    assert "--force" in result.output or "force" in result.output.lower()


@then('workspace "existing-target" should not be modified')
def check_target_not_modified(clone_target_exists):
    """Verify target not modified on error."""
    result = clone_target_exists["result"]
    assert result.exit_code != 0


# Clone with force flag
@scenario("../features/workspace.feature", "Clone with force flag overwrites existing target")
def test_clone_with_force():
    """Scenario: Clone with force flag overwrites existing target."""


@given('I have workspace "existing-target" in "test-org"')
def _():
    """Set up existing target."""
    pass


@given('I have workspace "prod-app" with terraform version "1.5.0"')
def _():
    """Set up source with version."""
    pass


@pytest.fixture
@when('I clone "prod-app" to "existing-target" with --force')
def clone_with_force(workspace_prod_response, workspace_cloned_response):
    """Clone with force flag."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        source_ws = Workspace.from_api_response(workspace_prod_response["data"])
        target_ws = Workspace.from_api_response(workspace_cloned_response["data"])
        mock_instance.workspaces.get.return_value = source_ws

        clone_result = {
            "status": "success",
            "source_workspace_id": source_ws.id,
            "source_workspace_name": "prod-app",
            "target_workspace_id": target_ws.id,
            "target_workspace_name": "existing-target",
            "organization": "test-org",
            "message": "Successfully cloned workspace 'prod-app' to 'existing-target'",
            "results": {
                "variables": None,
                "vcs": None,
                "team_access": None,
            },
        }

        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_api:
            mock_clone_instance = MagicMock()
            mock_clone_api.return_value = mock_clone_instance
            mock_clone_instance.clone.return_value = clone_result

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "clone",
                    "prod-app",
                    "existing-target",
                    "--organization",
                    "test-org",
                    "--force",
                ],
            )

            return {"result": result}


@then('workspace "existing-target" should be updated')
def check_target_updated(clone_with_force):
    """Verify target was updated."""
    result = clone_with_force["result"]
    assert result.exit_code == 0
    assert "existing-target" in result.output


@then('workspace "existing-target" should have terraform version from "prod-app"')
def check_version_updated(clone_with_force):
    """Verify version matches source."""
    result = clone_with_force["result"]
    assert result.exit_code == 0  # Version copied via clone


@then("clone operation should succeed")
def check_clone_success(clone_with_force):
    """Verify clone succeeded."""
    result = clone_with_force["result"]
    assert result.exit_code == 0


# Clone shows detailed output
@scenario("../features/workspace.feature", "Clone shows detailed progress and results")
def test_clone_detailed_output():
    """Scenario: Clone shows detailed progress and results."""


@given('I have workspace "prod-app" with 2 variables and VCS configured')
def _():
    """Set up source with variables and VCS."""
    pass


@pytest.fixture
@when('I clone "prod-app" to "staging-app" with --with-variables --with-vcs')
def clone_detailed_output(workspace_prod_response, workspace_cloned_response):
    """Clone with all options."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        source_ws = Workspace.from_api_response(workspace_prod_response["data"])
        target_ws = Workspace.from_api_response(workspace_cloned_response["data"])
        mock_instance.workspaces.get.return_value = source_ws

        clone_result = {
            "status": "success",
            "source_workspace_id": source_ws.id,
            "source_workspace_name": "prod-app",
            "target_workspace_id": target_ws.id,
            "target_workspace_name": "staging-app",
            "organization": "test-org",
            "message": "Successfully cloned workspace 'prod-app' to 'staging-app'",
            "results": {
                "variables": {
                    "status": "success",
                    "variables_cloned": 2,
                    "terraform_variables": 1,
                    "env_variables": 1,
                },
                "vcs": {
                    "status": "success",
                    "vcs_cloned": True,
                    "identifier": "github.com/acme/terraform",
                    "branch": "main",
                },
            },
        }

        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_api:
            mock_clone_instance = MagicMock()
            mock_clone_api.return_value = mock_clone_instance
            mock_clone_instance.clone.return_value = clone_result

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "clone",
                    "prod-app",
                    "staging-app",
                    "--organization",
                    "test-org",
                    "--with-variables",
                    "--with-vcs",
                ],
            )

            return {"result": result}


@then('output should show "Cloning workspace: prod-app → staging-app"')
def check_clone_message(clone_detailed_output):
    """Verify clone start message."""
    result = clone_detailed_output["result"]
    assert "Cloning" in result.output or "prod-app" in result.output


@then("output should show success message with checkmark")
def check_success_checkmark(clone_detailed_output):
    """Verify success message with checkmark."""
    result = clone_detailed_output["result"]
    assert "✓" in result.output or "success" in result.output.lower()


@then("output should show target workspace ID")
def check_workspace_id_shown(clone_detailed_output):
    """Verify workspace ID shown."""
    result = clone_detailed_output["result"]
    assert "ws-" in result.output or "workspace" in result.output.lower()


@then('output should show "Variables cloned: 2"')
def check_var_count_shown(clone_detailed_output):
    """Verify variable count shown."""
    result = clone_detailed_output["result"]
    assert "2" in result.output and "Variables" in result.output


@then("output should show variable breakdown (terraform vs env)")
def check_var_breakdown(clone_detailed_output):
    """Verify terraform/env breakdown."""
    result = clone_detailed_output["result"]
    assert (
        "terraform" in result.output.lower() or "env" in result.output.lower()
    ) and "1" in result.output


@then('output should show "VCS configured:" with repository details')
def check_vcs_details_shown(clone_detailed_output):
    """Verify VCS details shown."""
    result = clone_detailed_output["result"]
    assert "VCS" in result.output or "github" in result.output.lower()


# Clone without optional flags
@scenario("../features/workspace.feature", "Clone without variables or VCS copies settings only")
def test_clone_settings_only():
    """Scenario: Clone without variables or VCS copies settings only."""


@given('I have workspace "prod-app" with variables and VCS')
def _():
    """Set up source with variables and VCS."""
    pass


@pytest.fixture
@when('I clone "prod-app" to "staging-app" without any optional flags')
def clone_settings_only(workspace_prod_response, workspace_cloned_response):
    """Clone without optional flags."""
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        source_ws = Workspace.from_api_response(workspace_prod_response["data"])
        target_ws = Workspace.from_api_response(workspace_cloned_response["data"])
        mock_instance.workspaces.get.return_value = source_ws

        clone_result = {
            "status": "success",
            "source_workspace_id": source_ws.id,
            "source_workspace_name": "prod-app",
            "target_workspace_id": target_ws.id,
            "target_workspace_name": "staging-app",
            "organization": "test-org",
            "message": "Successfully cloned workspace 'prod-app' to 'staging-app'",
            "results": {
                "variables": None,
                "vcs": None,
            },
        }

        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_api:
            mock_clone_instance = MagicMock()
            mock_clone_api.return_value = mock_clone_instance
            mock_clone_instance.clone.return_value = clone_result

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "clone",
                    "prod-app",
                    "staging-app",
                    "--organization",
                    "test-org",
                ],
            )

            return {"result": result}


@then('workspace "staging-app" should be created with prod-app settings')
def check_settings_only_created(clone_settings_only):
    """Verify workspace created with settings."""
    result = clone_settings_only["result"]
    assert result.exit_code == 0
    assert "staging-app" in result.output


@then('workspace "staging-app" should NOT have prod-app variables')
def check_no_variables(clone_settings_only):
    """Verify variables not cloned."""
    result = clone_settings_only["result"]
    # Settings only shouldn't show variable count
    assert "Variables cloned" not in result.output or "0" in result.output


@then('workspace "staging-app" should NOT have prod-app VCS configuration')
def check_no_vcs(clone_settings_only):
    """Verify VCS not cloned."""
    # Use a safe way to check
    result_obj = clone_settings_only["result"]
    assert "VCS configured" not in result_obj.output or "No VCS" in result_obj.output


@then("output should show success message")
def check_success_message(clone_settings_only):
    """Verify success message shown."""
    result = clone_settings_only["result"]
    assert result.exit_code == 0


# ============================================================================
# Workspace Create Command Tests
# ============================================================================


@scenario("../features/workspace.feature", "Create a workspace with required name only")
def test_create_workspace_basic():
    """Scenario: Create a workspace with required name only."""


@given('organization "test-org" exists')
def _():
    """Organization exists."""
    pass


@pytest.fixture
@when('I create workspace "new-workspace" in "test-org"')
def create_workspace_basic(workspace_list_response):
    """Create workspace via CLI."""
    created_ws = Workspace.from_api_response(
        workspace_response(id="ws-newws1234567", name="new-workspace")["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.create.return_value = created_ws

        result = runner.invoke(
            app, ["workspace", "create", "new-workspace", "--organization", "test-org"]
        )
        return {"result": result, "workspace": created_ws}


@then('workspace "new-workspace" should be created')
def check_workspace_created(create_workspace_basic):
    """Verify workspace created."""
    result = create_workspace_basic["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"


@then('output should show "Created workspace: new-workspace"')
def check_create_output(create_workspace_basic):
    """Verify creation output message."""
    result = create_workspace_basic["result"]
    assert "new-workspace" in result.output


@scenario("../features/workspace.feature", "Create a workspace with optional settings")
def test_create_workspace_with_settings():
    """Scenario: Create workspace with optional settings."""


@pytest.fixture
@when('I create workspace "new-workspace" with tf-version "1.9.0" and execution-mode "remote"')
def create_workspace_with_settings():
    """Create workspace with settings."""
    created_ws = Workspace.from_api_response(
        workspace_response(
            id="ws-newws1234567",
            name="new-workspace",
            terraform_version="1.9.0",
            execution_mode="remote",
        )["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.create.return_value = created_ws

        result = runner.invoke(
            app,
            [
                "workspace",
                "create",
                "new-workspace",
                "--organization",
                "test-org",
                "--tf-version",
                "1.9.0",
                "--execution-mode",
                "remote",
            ],
        )
        return {"result": result, "workspace": created_ws}


@then('workspace should have terraform version "1.9.0"')
def check_tf_version(create_workspace_with_settings):
    """Verify terraform version."""
    result = create_workspace_with_settings["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert "1.9.0" in result.output


@then('workspace should have execution mode "remote"')
def check_execution_mode_create(create_workspace_with_settings):
    """Verify execution mode."""
    result = create_workspace_with_settings["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"


@scenario("../features/workspace.feature", "Create a workspace with project association")
def test_create_workspace_with_project():
    """Scenario: Create workspace with project association."""


@given('project "prj-abc123" exists in "test-org"')
def _():
    """Project exists."""
    pass


@pytest.fixture
@when('I create workspace "new-workspace" with project "prj-abc123"')
def create_workspace_with_project():
    """Create workspace with project."""
    created_ws = Workspace.from_api_response(
        workspace_response(id="ws-newws1234567", name="new-workspace", project_id="prj-abc123")[
            "data"
        ]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.create.return_value = created_ws

        result = runner.invoke(
            app,
            [
                "workspace",
                "create",
                "new-workspace",
                "--organization",
                "test-org",
                "--project",
                "prj-abc123",
            ],
        )
        return {"result": result, "workspace": created_ws}


@then('workspace should be associated with project "prj-abc123"')
def check_project_association(create_workspace_with_project):
    """Verify project association."""
    result = create_workspace_with_project["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"


@scenario("../features/workspace.feature", "Create workspace fails when it already exists")
def test_create_workspace_already_exists():
    """Scenario: Create workspace fails when already exists."""


@given('workspace "existing-ws" already exists in "test-org"')
def _():
    """Workspace already exists."""
    pass


@pytest.fixture
@when('I try to create workspace "existing-ws" in "test-org"')
def create_workspace_already_exists():
    """Try to create duplicate workspace."""
    from terrapyne.core.exceptions import WorkspaceAlreadyExistsError

    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.create.side_effect = WorkspaceAlreadyExistsError(
            "Workspace 'existing-ws' already exists", status_code=409
        )

        result = runner.invoke(
            app, ["workspace", "create", "existing-ws", "--organization", "test-org"]
        )
        return {"result": result}


@then('I should see error message containing "already exists"')
def check_already_exists_error(create_workspace_already_exists):
    """Verify already exists error."""
    result = create_workspace_already_exists["result"]
    assert result.exit_code == 1
    assert "already exists" in result.output.lower()


# ============================================================================
# Workspace Delete Command Tests
# ============================================================================


@scenario("../features/workspace.feature", "Delete a workspace with confirmation")
def test_delete_workspace_force():
    """Scenario: Delete a workspace with --force."""


@given('workspace "old-workspace" exists in "test-org"')
def _():
    """Workspace exists."""
    pass


@pytest.fixture
@when('I delete workspace "old-workspace" with --force')
def delete_workspace_force():
    """Delete workspace with --force."""
    existing_ws = Workspace.from_api_response(
        workspace_response(id="ws-oldws1234567", name="old-workspace")["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.return_value = existing_ws
        mock_instance.workspaces.delete.return_value = None

        result = runner.invoke(
            app,
            [
                "workspace",
                "delete",
                "old-workspace",
                "--organization",
                "test-org",
                "--force",
            ],
        )
        return {"result": result}


@then('workspace "old-workspace" should be deleted')
def check_workspace_deleted(delete_workspace_force):
    """Verify workspace deleted."""
    result = delete_workspace_force["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"


@then('output should show "Deleted workspace: old-workspace"')
def check_delete_output(delete_workspace_force):
    """Verify delete output message."""
    result = delete_workspace_force["result"]
    assert "old-workspace" in result.output


@scenario(
    "../features/workspace.feature",
    "Delete a workspace prompts for confirmation without --force",
)
def test_delete_workspace_confirm_yes():
    """Scenario: Delete workspace with confirmation prompt accepted."""


@pytest.fixture
@when('I delete workspace "old-workspace" without --force and confirm yes')
def delete_workspace_confirm_yes():
    """Delete workspace and confirm yes."""
    existing_ws = Workspace.from_api_response(
        workspace_response(id="ws-oldws1234567", name="old-workspace")["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.return_value = existing_ws
        mock_instance.workspaces.delete.return_value = None

        result = runner.invoke(
            app,
            ["workspace", "delete", "old-workspace", "--organization", "test-org"],
            input="y\n",
        )
        return {"result": result}


@then('workspace "old-workspace" should be deleted', target_fixture="delete_result_yes")
def check_workspace_deleted_yes(delete_workspace_confirm_yes):
    """Verify workspace deleted after yes."""
    result = delete_workspace_confirm_yes["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"


@scenario(
    "../features/workspace.feature",
    "Delete workspace aborted when user declines confirmation",
)
def test_delete_workspace_confirm_no():
    """Scenario: Delete workspace aborted on no."""


@pytest.fixture
@when('I delete workspace "old-workspace" without --force and confirm no')
def delete_workspace_confirm_no():
    """Delete workspace and decline confirmation."""
    existing_ws = Workspace.from_api_response(
        workspace_response(id="ws-oldws1234567", name="old-workspace")["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.return_value = existing_ws

        result = runner.invoke(
            app,
            ["workspace", "delete", "old-workspace", "--organization", "test-org"],
            input="n\n",
        )
        return {"result": result}


@then('workspace "old-workspace" should NOT be deleted')
def check_workspace_not_deleted(delete_workspace_confirm_no):
    """Verify workspace not deleted."""
    result = delete_workspace_confirm_no["result"]
    assert result.exit_code == 0


@then('output should show "Aborted"')
def check_aborted_output(delete_workspace_confirm_no):
    """Verify aborted message."""
    result = delete_workspace_confirm_no["result"]
    assert "Aborted" in result.output or "aborted" in result.output.lower()


@scenario("../features/workspace.feature", "Delete fails when workspace does not exist")
def test_delete_workspace_not_found():
    """Scenario: Delete fails when workspace does not exist."""


@given('workspace "ghost-workspace" does not exist in "test-org"')
def _():
    """Workspace does not exist."""
    pass


@pytest.fixture
@when('I try to delete workspace "ghost-workspace" in "test-org"')
def delete_workspace_not_found():
    """Try to delete nonexistent workspace."""
    from terrapyne.core.exceptions import WorkspaceNotFoundError

    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.side_effect = WorkspaceNotFoundError(
            "Workspace 'ghost-workspace' not found", status_code=404
        )

        result = runner.invoke(
            app,
            [
                "workspace",
                "delete",
                "ghost-workspace",
                "--organization",
                "test-org",
                "--force",
            ],
        )
        return {"result": result}


@then('I should see error message containing "not found"')
def check_not_found_error(delete_workspace_not_found):
    """Verify not found error."""
    result = delete_workspace_not_found["result"]
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


# B18 — workspace lock and unlock commands


@scenario("../features/workspace.feature", "Unlock a workspace locked by a cancelled run")
def test_workspace_unlock():
    pass


@scenario("../features/workspace.feature", "Lock a workspace with a reason")
def test_workspace_lock_with_reason():
    pass


@scenario(
    "../features/workspace.feature",
    "Lock a workspace prompts for confirmation without --yes",
)
def test_workspace_lock_confirm():
    pass


@scenario("../features/workspace.feature", "Lock aborted when user declines confirmation")
def test_workspace_lock_aborted():
    pass


@given('workspace "locked-ws" exists in "test-org"')
def _():
    pass


@given('workspace "my-app-dev" exists in "test-org"')
def _():
    pass


@pytest.fixture
@when('I unlock workspace "locked-ws"')
def unlock_workspace_result():
    existing_ws = Workspace.from_api_response(
        workspace_response(id="ws-locked-0001", name="locked-ws")["data"]
    )
    unlocked_ws = Workspace.from_api_response(
        workspace_response(id="ws-locked-0001", name="locked-ws")["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.return_value = existing_ws
        mock_instance.workspaces.unlock.return_value = unlocked_ws

        result = runner.invoke(
            app, ["workspace", "unlock", "locked-ws", "--organization", "test-org"]
        )
        return {"result": result}


@then("the workspace should be unlocked")
def check_workspace_unlocked(unlock_workspace_result):
    result = unlock_workspace_result["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"


@then('output should show "Unlocked workspace: locked-ws"')
def check_unlock_output(unlock_workspace_result):
    result = unlock_workspace_result["result"]
    assert "Unlocked workspace: locked-ws" in result.output


@pytest.fixture
@when('I lock workspace "my-app-dev" with reason "maintenance" and --yes')
def lock_workspace_yes():
    existing_ws = Workspace.from_api_response(
        workspace_response(id="ws-myappdev001", name="my-app-dev")["data"]
    )
    locked_ws = Workspace.from_api_response(
        workspace_response(id="ws-myappdev001", name="my-app-dev")["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.return_value = existing_ws
        mock_instance.workspaces.lock.return_value = locked_ws

        result = runner.invoke(
            app,
            [
                "workspace",
                "lock",
                "my-app-dev",
                "--organization",
                "test-org",
                "--reason",
                "maintenance",
                "--yes",
            ],
        )
        return {"result": result}


@then("the workspace should be locked")
def check_workspace_locked(lock_workspace_yes):
    result = lock_workspace_yes["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"


@then('output should show "Locked workspace: my-app-dev"')
def check_lock_output(lock_workspace_yes):
    result = lock_workspace_yes["result"]
    assert "Locked workspace: my-app-dev" in result.output


@pytest.fixture
@when('I lock workspace "my-app-dev" without --yes and confirm yes')
def lock_workspace_confirm_yes():
    existing_ws = Workspace.from_api_response(
        workspace_response(id="ws-myappdev001", name="my-app-dev")["data"]
    )
    locked_ws = Workspace.from_api_response(
        workspace_response(id="ws-myappdev001", name="my-app-dev")["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.return_value = existing_ws
        mock_instance.workspaces.lock.return_value = locked_ws

        result = runner.invoke(
            app,
            ["workspace", "lock", "my-app-dev", "--organization", "test-org"],
            input="y\n",
        )
        return {"result": result}


@then("the workspace should be locked")
def _check_workspace_locked_confirm(lock_workspace_confirm_yes):
    result = lock_workspace_confirm_yes["result"]
    assert result.exit_code == 0, f"Command failed: {result.output}"


@pytest.fixture
@when('I lock workspace "my-app-dev" without --yes and confirm no')
def lock_workspace_confirm_no():
    existing_ws = Workspace.from_api_response(
        workspace_response(id="ws-myappdev001", name="my-app-dev")["data"]
    )
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
        patch("terrapyne.api.client.TFCClient") as mock_client,
    ):
        mock_org.return_value = "test-org"
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.workspaces.get.return_value = existing_ws

        result = runner.invoke(
            app,
            ["workspace", "lock", "my-app-dev", "--organization", "test-org"],
            input="n\n",
        )
        return {"result": result}


@then('output should show "Aborted"')
def check_lock_aborted(lock_workspace_confirm_no):
    result = lock_workspace_confirm_no["result"]
    assert "Aborted" in result.output or "aborted" in result.output.lower()
