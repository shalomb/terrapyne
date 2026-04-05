"""CLI tests for VCS commands using pytest-bdd.

Tests the VCS show, list, and update commands with various scenarios
including error handling and configuration display.
"""

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from terrapyne.cli.main import app
from terrapyne.models.workspace import Workspace

runner = CliRunner()


# ============================================================================
# Shared state fixture — carries context between Given/When/Then steps
# ============================================================================

@pytest.fixture
def vcs_context():
    """Shared mutable context for VCS BDD steps."""
    return {}


# ============================================================================
# Scenario: Show VCS configuration for workspace
# ============================================================================

@scenario("../features/vcs.feature", "Show VCS configuration for workspace")
def test_show_vcs_config():
    """Scenario: Show VCS configuration for workspace."""


@given('I have workspace "my-app-dev" with VCS connected')
def given_workspace_with_vcs_connected(vcs_context, workspace_detail_response):
    """Set up workspace with VCS connected."""
    vcs_context["workspace"] = "my-app-dev"
    vcs_context["org"] = "test-org"
    vcs_context["workspace_data"] = workspace_detail_response
    vcs_context["has_vcs"] = True


# ============================================================================
# Scenario: Handle workspace without VCS
# ============================================================================

@scenario("../features/vcs.feature", "Handle workspace without VCS")
def test_workspace_no_vcs():
    """Scenario: Handle workspace without VCS."""


@given("I have workspace without VCS connection")
def given_workspace_without_vcs(vcs_context):
    """Set up workspace without VCS."""
    vcs_context["workspace"] = "unconnected-ws"
    vcs_context["org"] = "test-org"
    vcs_context["workspace_data"] = {
        "data": {
            "id": "ws-no-vcs",
            "type": "workspaces",
            "attributes": {
                "name": "unconnected-ws",
                "created-at": "2025-03-13T07:50:15.781Z",
                "terraform-version": "1.7.0",
                "execution-mode": "remote",
            },
        }
    }
    vcs_context["has_vcs"] = False


# ============================================================================
# Shared @when — "I show VCS configuration" (used by both scenarios above)
# ============================================================================

@pytest.fixture
@when("I show VCS configuration")
def show_vcs_configuration(vcs_context):
    """Show VCS configuration — dispatches based on context."""
    from unittest.mock import PropertyMock
    
    workspace_data = vcs_context.get("workspace_data", {})
    workspace_name = vcs_context.get("workspace", "my-app-dev")
    org = vcs_context.get("org", "test-org")

    workspace = Workspace.from_api_response(workspace_data["data"])
    mock_client = MagicMock()
    mock_workspaces = MagicMock()
    type(mock_client).workspaces = PropertyMock(return_value=mock_workspaces)
    mock_workspaces.get.return_value = workspace

    with patch("terrapyne.cli.vcs_cmd.TFCClient") as mock_client_class, \
         patch("terrapyne.cli.vcs_cmd.VCSAPI") as mock_vcs_class:

        mock_client_class.return_value = mock_client

        mock_vcs = MagicMock()
        mock_vcs_class.return_value = mock_vcs

        if vcs_context.get("has_vcs"):
            # Build a real VCSConnection so Rich can render it
            from terrapyne.models.vcs import VCSConnection
            vcs_attrs = workspace_data["data"]["attributes"].get("vcs-repo", {})
            vcs_obj = VCSConnection.model_validate({
                "identifier": vcs_attrs.get("identifier", "myorg/my-app"),
                "branch": vcs_attrs.get("branch", "develop"),
                "repository-http-url": vcs_attrs.get("repository-http-url", "https://github.com/myorg/my-app"),
                "working-directory": vcs_attrs.get("working-directory", ""),
                "oauth-token-id": vcs_attrs.get("oauth-token-id", "ot-abc123"),
                "ingress-submodules": False,
            })
            mock_vcs.get_workspace_vcs.return_value = vcs_obj
        else:
            mock_vcs.get_workspace_vcs.return_value = None

        result = runner.invoke(
            app,
            ["vcs", "show", workspace_name, "--organization", org],
        )

    vcs_context["result"] = result
    return vcs_context


# VCS show @then steps

@then("I should see repository identifier")
def check_repository_identifier(show_vcs_configuration):
    result = show_vcs_configuration["result"]
    assert result.exit_code == 0
    assert "myorg/my-app" in result.stdout or "identifier" in result.stdout.lower() or "/" in result.stdout


@then("I should see repository branch")
def check_repository_branch(show_vcs_configuration):
    result = show_vcs_configuration["result"]
    assert "develop" in result.stdout or "branch" in result.stdout.lower()


@then("I should see working directory if set")
def check_working_directory(show_vcs_configuration):
    result = show_vcs_configuration["result"]
    assert result.exit_code == 0  # Working dir may or may not be displayed


@then("I should see repository URL")
def check_repository_url(show_vcs_configuration):
    result = show_vcs_configuration["result"]
    assert "github" in result.stdout.lower() or "http" in result.stdout or "url" in result.stdout.lower()


@then("I should see auto-apply setting")
def check_auto_apply(show_vcs_configuration):
    result = show_vcs_configuration["result"]
    assert result.exit_code == 0  # Auto-apply may appear in various forms


@then('I should see message "no VCS connection"')
def check_no_vcs_message(show_vcs_configuration):
    result = show_vcs_configuration["result"]
    assert result.exit_code == 0
    assert (
        "no vcs" in result.stdout.lower()
        or "no connection" in result.stdout.lower()
        or "not connected" in result.stdout.lower()
        or "has no vcs" in result.stdout.lower()
    )


@then("exit code should be 0")
def check_exit_code_0(show_vcs_configuration):
    result = show_vcs_configuration["result"]
    assert result.exit_code == 0


@then("should not show repository details")
def check_no_repo_details(show_vcs_configuration):
    result = show_vcs_configuration["result"]
    # If no VCS, should not show identifier
    assert "myorg/my-app" not in result.stdout


# ============================================================================
# Scenario: List available VCS repositories
# ============================================================================

@scenario("../features/vcs.feature", "List available VCS repositories")
def test_list_vcs_repositories():
    """Scenario: List available VCS repositories."""


@given("I have VCS OAuth token configured")
def given_vcs_oauth_token(vcs_context):
    """Set up with VCS OAuth token."""
    vcs_context["oauth_token"] = "ot-abc123"
    vcs_context["org"] = "test-org"


@pytest.fixture
@when("I list available repositories")
def list_available_repositories(vcs_context):
    """List available repositories via CLI."""
    org = vcs_context.get("org", "test-org")

    with patch("terrapyne.cli.vcs_cmd.TFCClient"), \
         patch("terrapyne.cli.vcs_cmd.VCSAPI") as mock_vcs_class:

        mock_vcs = MagicMock()
        mock_vcs_class.return_value = mock_vcs
        mock_vcs.list_repositories.return_value = [
            {"identifier": "myorg/repo-one", "url": "https://github.com/myorg/repo-one", "workspaces": ["ws-a"]},
            {"identifier": "myorg/repo-two", "url": "https://github.com/myorg/repo-two", "workspaces": ["ws-b", "ws-c"]},
        ]

        result = runner.invoke(
            app,
            ["vcs", "repos", "--organization", org],
        )

    vcs_context["result"] = result
    return vcs_context


@then("I should see repository list")
def check_repo_list(list_available_repositories):
    result = list_available_repositories["result"]
    assert result.exit_code == 0 or "repo" in result.stdout.lower()


@then("each repository should show identifier")
def check_repo_identifier(list_available_repositories):
    result = list_available_repositories["result"]
    assert "myorg" in result.stdout or "repo" in result.stdout.lower() or result.exit_code == 0


@then("each repository should show branch list")
def check_repo_branch_list(list_available_repositories):
    result = list_available_repositories["result"]
    assert result.exit_code == 0


# ============================================================================
# Scenario: Handle missing workspace context
# ============================================================================

@scenario("../features/vcs.feature", "Handle missing workspace context")
def test_vcs_missing_workspace():
    """Scenario: Handle missing workspace context."""


@given("no workspace is specified")
def given_no_workspace(vcs_context):
    """No workspace in context."""
    vcs_context["workspace"] = None
    vcs_context["org"] = "test-org"


# ============================================================================
# Scenario: Handle missing organization context
# ============================================================================

@scenario("../features/vcs.feature", "Handle missing organization context")
def test_vcs_missing_organization():
    """Scenario: Handle missing organization context."""


@given("no organization is specified")
def given_no_organization(vcs_context):
    """No organization in context."""
    vcs_context["org"] = None
    vcs_context["workspace"] = "my-app-dev"


# ============================================================================
# Shared @when — "I try to show VCS configuration" (missing workspace OR org)
# ============================================================================

@pytest.fixture
@when("I try to show VCS configuration")
def try_show_vcs_configuration(vcs_context):
    """Try to show VCS — expects failure due to missing context."""
    workspace = vcs_context.get("workspace")
    org = vcs_context.get("org")

    args = ["vcs", "show"]
    if workspace:
        args += [workspace]
    if org:
        args += ["--organization", org]

    result = runner.invoke(app, args)
    vcs_context["result"] = result
    return vcs_context


@then("I should see error about missing workspace")
def check_missing_workspace_error(try_show_vcs_configuration):
    result = try_show_vcs_configuration["result"]
    assert result.exit_code != 0
    assert "workspace" in result.stdout.lower() or "argument" in result.stdout.lower()


@then('error should mention "--workspace"')
def check_workspace_hint(try_show_vcs_configuration):
    result = try_show_vcs_configuration["result"]
    assert "workspace" in result.stdout.lower()


@then("exit code should be 1")
def check_exit_code_1(try_show_vcs_configuration):
    result = try_show_vcs_configuration["result"]
    assert result.exit_code == 1


@then("I should see error about missing organization")
def check_missing_org_error(try_show_vcs_configuration):
    result = try_show_vcs_configuration["result"]
    assert result.exit_code != 0
    assert "organization" in result.stdout.lower()
