"""Tests for 'state outputs --raw' flag."""
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from terrapyne.cli.main import app
from terrapyne.models.state_version import StateVersionOutput

runner = CliRunner()

@pytest.fixture
def mock_client():
    with patch("terrapyne.cli.state_cmd.TFCClient") as mock_client_class, \
         patch("terrapyne.cli.state_cmd.validate_context") as mock_validate:
        
        mock_instance = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_instance
        
        # Mock context: org="test-org", workspace="test-ws"
        mock_validate.return_value = ("test-org", "test-ws")
        
        # Mock workspace get
        mock_ws = MagicMock()
        mock_ws.id = "ws-123"
        mock_instance.workspaces.get.return_value = mock_ws
        
        # Mock latest state version
        mock_sv = MagicMock()
        mock_sv.id = "sv-123"
        mock_instance.state_versions.get_current.return_value = mock_sv
        
        yield mock_instance

def test_state_outputs_raw_single_value(mock_client):
    """Should print unquoted value when --raw is used with a single output."""
    mock_client.state_versions.list_outputs.return_value = [
        StateVersionOutput(name="api_url", value="https://api.example.com", type="string", sensitive=False)
    ]
    
    result = runner.invoke(app, ["state", "outputs", "--raw"])
    
    assert result.exit_code == 0
    assert result.stdout.strip() == "https://api.example.com"

def test_state_outputs_raw_specific_name(mock_client):
    """Should print unquoted value for a specific named output when --raw is used."""
    mock_client.state_versions.list_outputs.return_value = [
        StateVersionOutput(name="a", value="1", type="string", sensitive=False),
        StateVersionOutput(name="b", value="2", type="string", sensitive=False)
    ]
    
    # We want to support: tfc state outputs test-ws b --raw
    result = runner.invoke(app, ["state", "outputs", "test-ws", "b", "--raw"])
    
    assert result.exit_code == 0
    assert result.stdout.strip() == "2"
