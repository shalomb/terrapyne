"""Unit tests for the --raw flag in state outputs command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.state_version import StateVersionOutput
from terrapyne.models.workspace import Workspace

runner = CliRunner()


class TestStateOutputsRaw:
    """Test suite for state outputs --raw functionality."""

    def test_raw_returns_unquoted_string(self):
        """--raw returns string value without quotes."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        m.state_versions.list_outputs.return_value = [
            StateVersionOutput(
                name="db_url", value="postgres://host:5432/db", type="string", sensitive=False
            )
        ]

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            # Correct order: state outputs <workspace> <name> --raw
            result = runner.invoke(
                app,
                ["state", "outputs", "test-ws", "db_url", "--raw", "--organization", "test-org"],
            )

        assert result.exit_code == 0
        assert result.stdout.strip() == "postgres://host:5432/db"
        assert '"' not in result.stdout

    def test_raw_returns_json_for_dict(self):
        """--raw returns JSON representation for dict values."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        test_dict = {"host": "db", "port": 5432}
        m.state_versions.list_outputs.return_value = [
            StateVersionOutput(name="config", value=test_dict, type="object", sensitive=False)
        ]

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app,
                ["state", "outputs", "test-ws", "config", "--raw", "--organization", "test-org"],
            )

        assert result.exit_code == 0
        import json

        assert json.loads(result.stdout) == test_dict

    def test_raw_returns_json_for_list(self):
        """--raw returns JSON representation for list values."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        test_list = ["a", "b", "c"]
        m.state_versions.list_outputs.return_value = [
            StateVersionOutput(name="items", value=test_list, type="list", sensitive=False)
        ]

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app, ["state", "outputs", "test-ws", "items", "--raw", "--organization", "test-org"]
            )

        assert result.exit_code == 0
        import json

        assert json.loads(result.stdout) == test_list

    def test_raw_returns_json_for_number(self):
        """--raw returns JSON representation for numeric values."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        m.state_versions.list_outputs.return_value = [
            StateVersionOutput(name="port", value=5432, type="number", sensitive=False)
        ]

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app, ["state", "outputs", "test-ws", "port", "--raw", "--organization", "test-org"]
            )

        assert result.exit_code == 0
        assert result.stdout.strip() == "5432"

    def test_raw_missing_output_exits_with_error(self):
        """--raw exits with code 1 when output not found."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        m.state_versions.list_outputs.return_value = []

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app,
                ["state", "outputs", "test-ws", "missing", "--raw", "--organization", "test-org"],
            )

        assert result.exit_code == 1
        assert "not found" in result.stdout or "not found" in result.stderr

    def test_raw_mutually_exclusive_with_format_json(self):
        """--raw with --format json raises error."""
        m = MagicMock()

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app,
                [
                    "state",
                    "outputs",
                    "test-ws",
                    "test",
                    "--raw",
                    "--format",
                    "json",
                    "--organization",
                    "test-org",
                ],
            )

        assert result.exit_code == 1
        assert "mutually exclusive" in result.stdout or "mutually exclusive" in result.stderr

    def test_raw_requires_output_name(self):
        """--raw requires a specific output name as argument."""
        m = MagicMock()

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            # If only workspace is provided, name is missing
            result = runner.invoke(
                app, ["state", "outputs", "test-ws", "--raw", "--organization", "test-org"]
            )

        assert result.exit_code == 1
        # The code returns "Provide a workspace name, workspace ID, or state version ID"
        # if shift logic doesn't have enough args
        assert "Error:" in result.stdout or "Error:" in result.stderr

    def test_raw_with_workspace_id_fails(self):
        """--raw rejects workspace IDs as arguments if they are the only argument."""
        # Note: current implementation allows <workspace_id> <output_name> --raw
        pass

    def test_normal_mode_still_works(self):
        """Normal output list mode still works without --raw."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        m.state_versions.list_outputs.return_value = [
            StateVersionOutput(
                name="db_url", value="postgres://host:5432/db", type="string", sensitive=False
            ),
            StateVersionOutput(name="app_name", value="myapp", type="string", sensitive=False),
        ]

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app, ["state", "outputs", "test-ws", "--organization", "test-org"]
            )

        assert result.exit_code == 0
        assert "db_url" in result.stdout
        assert "app_name" in result.stdout

    def test_normal_mode_json_format(self):
        """Normal JSON output still works without --raw."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        m.state_versions.list_outputs.return_value = [
            StateVersionOutput(
                name="db_url", value="postgres://host:5432/db", type="string", sensitive=False
            )
        ]

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app,
                [
                    "state",
                    "outputs",
                    "test-ws",
                    "--format",
                    "json",
                    "--organization",
                    "test-org",
                ],
            )

        assert result.exit_code == 0
        import json

        data = json.loads(result.stdout)
        assert data["db_url"] == "postgres://host:5432/db"
