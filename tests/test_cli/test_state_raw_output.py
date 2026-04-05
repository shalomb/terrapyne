"""Unit tests for --raw flag in state outputs command."""
import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.state_version import StateVersionOutput
from terrapyne.models.workspace import Workspace

runner = CliRunner()


class TestStateOutputsRaw:
    """Tests for --raw flag functionality."""

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
            result = runner.invoke(
                app, ["state", "outputs", "db_url", "-w", "test-ws", "-o", "test-org", "--raw"]
            )

        assert result.exit_code == 0
        assert result.stdout.strip() == "postgres://host:5432/db"
        # Ensure no ANSI codes
        assert "\033[" not in result.stdout
        assert "\x1b[" not in result.stdout
        # Ensure no table formatting
        assert "│" not in result.stdout

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
                app, ["state", "outputs", "config", "-w", "test-ws", "-o", "test-org", "--raw"]
            )

        assert result.exit_code == 0
        output_json = json.loads(result.stdout)
        assert output_json == test_dict

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
                app, ["state", "outputs", "items", "-w", "test-ws", "-o", "test-org", "--raw"]
            )

        assert result.exit_code == 0
        output_json = json.loads(result.stdout)
        assert output_json == test_list

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
                app, ["state", "outputs", "port", "-w", "test-ws", "-o", "test-org", "--raw"]
            )

        assert result.exit_code == 0
        output_json = json.loads(result.stdout)
        assert output_json == 5432

    def test_raw_missing_output_exits_with_error(self):
        """--raw exits with code 1 when output not found."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        m.state_versions.list_outputs.return_value = []

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app, ["state", "outputs", "missing", "-w", "test-ws", "-o", "test-org", "--raw"]
            )

        assert result.exit_code == 1
        assert "not found" in result.stdout

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
                    "test",
                    "-w",
                    "test-ws",
                    "-o",
                    "test-org",
                    "--raw",
                    "--format",
                    "json",
                ],
            )

        assert result.exit_code == 1
        assert "mutually exclusive" in result.stdout

    def test_raw_requires_output_name(self):
        """--raw requires a specific output name as argument."""
        m = MagicMock()

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app, ["state", "outputs", "-w", "test-ws", "-o", "test-org", "--raw"]
            )

        assert result.exit_code == 1
        assert "Output name required" in result.stdout

    def test_raw_with_workspace_id_fails(self):
        """--raw rejects workspace IDs as arguments."""
        m = MagicMock()

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app,
                ["state", "outputs", "ws-abc", "-w", "test-ws", "-o", "test-org", "--raw"],
            )

        assert result.exit_code == 1
        assert "not workspace ID" in result.stdout

    def test_raw_with_state_version_id_fails(self):
        """--raw rejects state version IDs as arguments."""
        m = MagicMock()

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app,
                ["state", "outputs", "sv-xyz", "-w", "test-ws", "-o", "test-org", "--raw"],
            )

        assert result.exit_code == 1
        assert "not workspace ID" in result.stdout

    def test_normal_mode_still_works(self):
        """Normal output list mode still works without --raw."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        m.state_versions.list_outputs.return_value = [
            StateVersionOutput(name="db_url", value="postgres://host:5432/db", type="string", sensitive=False),
            StateVersionOutput(name="app_name", value="myapp", type="string", sensitive=False),
        ]

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app, ["state", "outputs", "-w", "test-ws", "-o", "test-org"]
            )

        assert result.exit_code == 0
        # Table formatting should be present in normal mode
        assert "State Outputs" in result.stdout or "db_url" in result.stdout

    def test_normal_mode_json_format(self):
        """Normal JSON output still works without --raw."""
        m = MagicMock()
        m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="test-ws")
        m.state_versions.get_current.return_value = MagicMock(id="sv-xyz")
        m.state_versions.list_outputs.return_value = [
            StateVersionOutput(name="db_url", value="postgres://host:5432/db", type="string", sensitive=False)
        ]

        with patch("terrapyne.cli.state_cmd.TFCClient") as c:
            c.return_value.__enter__.return_value = m
            result = runner.invoke(
                app,
                [
                    "state",
                    "outputs",
                    "-w",
                    "test-ws",
                    "-o",
                    "test-org",
                    "--format",
                    "json",
                ],
            )

        assert result.exit_code == 0
        output_json = json.loads(result.stdout)
        assert isinstance(output_json, list)
        assert len(output_json) == 1
        assert output_json[0]["name"] == "db_url"
