"""CLI tests for workspace set-branch command (F13)."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.workspace import Workspace
from tests.fixtures.factories import workspace_response

runner = CliRunner()


def _make_workspace(vcs_branch="feature/my-change", with_vcs=True):
    vcs_repo = (
        {
            "identifier": "myorg/my-app",
            "branch": vcs_branch,
            "repository-http-url": "https://github.com/myorg/my-app",
            "oauth-token-id": "ot-abc123",
        }
        if with_vcs
        else None
    )
    resp = workspace_response(name="my-app-dev", vcs_repo=vcs_repo)
    return Workspace.from_api_response(resp["data"])


class TestWorkspaceSetBranchCommand:
    """CLI integration tests for tfc workspace set-branch."""

    def test_set_branch_success(self):
        """set-branch succeeds and prints updated branch."""
        updated_ws = _make_workspace(vcs_branch="feature/my-change")

        with (
            patch("terrapyne.cli.workspace_cmd.resolve_organization") as mock_org,
            patch("terrapyne.api.client.TFCClient") as mock_client_cls,
        ):
            mock_org.return_value = "test-org"
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance
            mock_instance.workspaces.set_vcs_branch.return_value = updated_ws

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "set-branch",
                    "my-app-dev",
                    "feature/my-change",
                    "--organization",
                    "test-org",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "feature/my-change" in result.output

    def test_set_branch_calls_api_with_correct_args(self):
        """set-branch passes workspace name, branch, and org to the API."""
        updated_ws = _make_workspace(vcs_branch="hotfix/123")

        with (
            patch("terrapyne.cli.workspace_cmd.resolve_organization") as mock_org,
            patch("terrapyne.api.client.TFCClient") as mock_client_cls,
        ):
            mock_org.return_value = "test-org"
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance
            mock_instance.workspaces.set_vcs_branch.return_value = updated_ws

            runner.invoke(
                app,
                [
                    "workspace",
                    "set-branch",
                    "my-app-dev",
                    "hotfix/123",
                    "--organization",
                    "test-org",
                ],
            )

        mock_instance.workspaces.set_vcs_branch.assert_called_once_with(
            workspace_name="my-app-dev",
            branch="hotfix/123",
            organization="test-org",
        )

    def test_set_branch_no_vcs_exits_with_error(self):
        """set-branch exits 1 with an error when workspace has no VCS."""
        with (
            patch("terrapyne.cli.workspace_cmd.resolve_organization") as mock_org,
            patch("terrapyne.api.client.TFCClient") as mock_client_cls,
        ):
            mock_org.return_value = "test-org"
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance
            mock_instance.workspaces.set_vcs_branch.side_effect = ValueError(
                "Workspace 'no-vcs-ws' has no VCS connection."
            )

            result = runner.invoke(
                app,
                [
                    "workspace",
                    "set-branch",
                    "no-vcs-ws",
                    "feature/new",
                    "--organization",
                    "test-org",
                ],
            )

        assert result.exit_code == 1
        assert "no VCS" in (result.output + result.stderr) or "Error" in (
            result.output + result.stderr
        )

    def test_set_branch_requires_organization(self):
        """set-branch exits 1 when no organization is available."""
        with patch("terrapyne.cli.workspace_cmd.resolve_organization") as mock_org:
            mock_org.return_value = None

            result = runner.invoke(
                app,
                ["workspace", "set-branch", "my-app-dev", "feature/x"],
            )

        assert result.exit_code == 1
        assert "Organization" in result.output or "organization" in result.output
