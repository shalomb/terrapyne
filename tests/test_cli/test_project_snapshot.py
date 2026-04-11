"""Tests for 'project show' enrichment."""
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from terrapyne.models.project import Project
from terrapyne.models.workspace import Workspace

runner = CliRunner()

def test_project_show_snapshot():
    """tfc project show should show a 'single glance' snapshot."""
    # Patch EVERYWHERE it might be imported from
    with patch("terrapyne.cli.project_cmd.validate_context") as mock_val, \
         patch("terrapyne.cli.project_cmd.resolve_project_context") as mock_res, \
         patch("terrapyne.cli.project_cmd.TFCClient") as mock_client, \
         patch("terrapyne.cli.project_cmd.WorkspaceAPI") as mock_ws_api:
        
        # Configure mocks
        mock_val.return_value = ("test-org", None)
        
        project = Project.model_construct(id="prj-1", name="test-project")
        mock_res.return_value = ("test-org", project)
        
        client_instance = mock_client.return_value.__enter__.return_value
        
        # Mock WorkspaceAPI.list
        ws_api_instance = mock_ws_api.return_value
        ws = Workspace.model_construct(id="ws-1", name="app-prod", locked=False)
        ws_api_instance.list.return_value = (iter([ws]), 1)
        
        # Mock client.runs.list for active count
        client_instance.runs.list.return_value = ([], 0)
        
        from terrapyne.cli.main import app
        result = runner.invoke(app, ["project", "show", "test-project"])
        
        assert result.exit_code == 0, f"STDOUT: {result.stdout}"
        assert "Project Snapshot" in result.stdout
        assert "Workspaces" in result.stdout
        assert "Active Runs" in result.stdout
