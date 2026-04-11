"""Tests for --json output in 'show' commands."""
import pytest
import json
import sys
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from terrapyne.models.project import Project
from terrapyne.models.workspace import Workspace

runner = CliRunner()

def test_project_show_json():
    """tfc project show --format json should return structured output."""
    # Patch at the very root of where it is used
    with patch("terrapyne.cli.project_cmd.validate_context") as mock_val, \
         patch("terrapyne.cli.project_cmd.resolve_project_context") as mock_res, \
         patch("terrapyne.cli.project_cmd.TFCClient") as mock_client, \
         patch("terrapyne.cli.project_cmd.WorkspaceAPI") as mock_ws_api:
        
        # Configure mocks
        mock_val.return_value = ("test-org", None)
        
        project = Project.model_construct(id="prj-1", name="test-project", description="desc")
        mock_res.return_value = ("test-org", project)
        
        client_instance = mock_client.return_value.__enter__.return_value
        
        ws_api_instance = mock_ws_api.return_value
        ws_api_instance.list.return_value = ([], 0)
        
        # We need to import app AFTER patching if possible, or use the already imported one
        from terrapyne.cli.main import app
        
        result = runner.invoke(app, ["project", "show", "test-project", "--format", "json"])
        
        assert result.exit_code == 0, f"STDOUT: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["project"]["name"] == "test-project"
        assert "workspaces" in data

def test_workspace_show_json():
    """tfc workspace show --format json should return enriched structured output."""
    with patch("terrapyne.cli.workspace_cmd.validate_context") as mock_val, \
         patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        
        mock_val.return_value = ("test-org", "test-ws")
        
        client_instance = mock_client.return_value.__enter__.return_value
        
        ws = Workspace.model_construct(id="ws-1", name="test-ws", project_id="prj-1")
        client_instance.workspaces.get.return_value = ws
        client_instance.runs.list.return_value = ([], 0)
        client_instance.workspaces.get_variables.return_value = []
        
        from terrapyne.cli.main import app
        
        result = runner.invoke(app, ["workspace", "show", "test-ws", "--format", "json"])
        
        assert result.exit_code == 0, f"STDOUT: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["workspace"]["name"] == "test-ws"
        assert "activity" in data
