"""Tests for run log streaming."""
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from terrapyne.cli.main import app
from terrapyne.models.run import Run, RunStatus

runner = CliRunner()

@pytest.fixture
def mock_client():
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client_class, \
         patch("terrapyne.cli.run_cmd.validate_context") as mock_validate:
        
        mock_instance = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_instance
        mock_validate.return_value = ("test-org", "test-ws")
        
        # Mock workspace
        mock_ws = MagicMock()
        mock_ws.id = "ws-123"
        mock_ws.name = "test-ws"
        mock_instance.workspaces.get.return_value = mock_ws
        
        yield mock_instance

def test_run_trigger_stream_logs(monkeypatch):
    """tfc run trigger --stream should accept flag and call stream helper."""
    from terrapyne.cli import run_cmd
    
    # Mock dependencies
    mock_client = MagicMock()
    mock_client_instance = mock_client.return_value.__enter__.return_value
    monkeypatch.setattr(run_cmd, "TFCClient", mock_client)
    
    mock_val = MagicMock(return_value=("test-org", "test-ws"))
    monkeypatch.setattr(run_cmd, "validate_context", mock_val)
    
    mock_ws = MagicMock()
    mock_ws.id = "ws-123"
    mock_client_instance.workspaces.get.return_value = mock_ws
    
    # Mock the run creation
    run = Run.model_construct(id="run-1", status=RunStatus.PENDING, plan_id="p-1")
    mock_client_instance.runs.create.return_value = run
    
    # Mock the streaming helper to return immediately
    final_run = Run.model_construct(id="run-1", status=RunStatus.APPLIED, plan_id="p-1")
    mock_stream = MagicMock(return_value=final_run)
    monkeypatch.setattr(run_cmd, "_stream_run_logs", mock_stream)
    
    # Mock render helper
    monkeypatch.setattr(run_cmd, "render_run_detail", MagicMock())

    result = runner.invoke(app, ["run", "trigger", "test-ws", "--stream"])
    
    assert result.exit_code == 0
    assert mock_stream.called
