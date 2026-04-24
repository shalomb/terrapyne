"""Tests for workspace CLI context auto-detection bug fixes."""

from unittest.mock import MagicMock, patch


class TestWorkspaceContextResolution:
    """workspace show/variables/vcs all had org, _ = validate_context()
    discarding the resolved workspace name, then passing workspace or ""
    downstream — causing a crash when invoked without explicit args."""

    def _make_workspace(self, name="my-workspace"):
        from terrapyne.models.workspace import Workspace

        ws = MagicMock(spec=Workspace)
        ws.id = "ws-abc123"
        ws.name = name
        ws.terraform_version = "~>1.12.0"
        ws.execution_mode = "agent"
        ws.auto_apply = False
        ws.locked = False
        ws.vcs_repo = None
        ws.tag_names = []
        ws.environment = "development"
        ws.project_id = "prj-xyz"
        ws.created_at = None
        ws.updated_at = None
        ws.working_directory = "iac/dev"
        ws.latest_run = None
        return ws

    @patch("terrapyne.cli.workspace_cmd.validate_context")
    @patch("terrapyne.cli.workspace_cmd.TFCClient")
    def test_workspace_show_uses_resolved_name(self, mock_client_cls, mock_validate):
        """workspace show must pass the resolved workspace name to .get(), not raw arg."""
        from typer.testing import CliRunner

        from terrapyne.cli.workspace_cmd import app

        resolved_ws_name = "auto-detected-workspace"
        mock_validate.return_value = ("MyOrg", resolved_ws_name)

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = lambda s: mock_client
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.workspaces.get.return_value = self._make_workspace(resolved_ws_name)
        mock_client.workspaces.get_variables.return_value = []
        mock_client.runs.list.return_value = ([], 0)

        runner = CliRunner()
        result = runner.invoke(app, ["show"])  # no workspace arg

        # Must not crash and must have called .get() with the resolved name
        mock_client.workspaces.get.assert_called_once_with(
            resolved_ws_name,
            "MyOrg",
            include="project,latest-run,latest-run.configuration-version",
        )
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"

    @patch("terrapyne.cli.workspace_cmd.validate_context")
    @patch("terrapyne.cli.workspace_cmd.TFCClient")
    def test_workspace_variables_uses_resolved_name(self, mock_client_cls, mock_validate):
        """workspace variables must pass resolved name to .get(), not empty string."""
        from typer.testing import CliRunner

        from terrapyne.cli.workspace_cmd import app

        resolved_ws_name = "auto-detected-workspace"
        mock_validate.return_value = ("MyOrg", resolved_ws_name)

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = lambda s: mock_client
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.workspaces.get.return_value = self._make_workspace(resolved_ws_name)
        mock_client.workspaces.get_variables.return_value = []

        runner = CliRunner()
        result = runner.invoke(app, ["variables"])

        mock_client.workspaces.get.assert_called_once_with(resolved_ws_name, "MyOrg")
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"

    @patch("terrapyne.cli.workspace_cmd.validate_context")
    @patch("terrapyne.cli.workspace_cmd.TFCClient")
    def test_workspace_vcs_uses_resolved_name(self, mock_client_cls, mock_validate):
        """workspace vcs must pass resolved name to .get(), not empty string."""
        from typer.testing import CliRunner

        from terrapyne.cli.workspace_cmd import app

        resolved_ws_name = "auto-detected-workspace"
        mock_validate.return_value = ("MyOrg", resolved_ws_name)

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = lambda s: mock_client
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ws = self._make_workspace(resolved_ws_name)
        mock_client.workspaces.get.return_value = mock_ws
        mock_client.workspaces.get_variables.return_value = []

        runner = CliRunner()
        result = runner.invoke(app, ["vcs"])

        mock_client.workspaces.get.assert_called_once_with(resolved_ws_name, "MyOrg")
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"
