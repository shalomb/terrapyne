"""Tests for --debug flag."""
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from terrapyne.cli.main import app

runner = CliRunner()

def test_global_debug_flag_accepted(monkeypatch):
    """terrapyne --debug should be accepted and enable debug mode."""
    from terrapyne.cli import utils
    
    # Track calls to set_debug
    mock_set_debug = MagicMock()
    monkeypatch.setattr(utils, "set_debug", mock_set_debug)

    # Run with debug and version (version exits early)
    result = runner.invoke(app, ["--debug", "--version"])
    
    assert result.exit_code == 0
    mock_set_debug.assert_called_with(True)
