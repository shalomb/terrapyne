"""Test that CLI commands use client.projects, client.workspaces properties instead of direct instantiation.

This test verifies the standardised API access pattern: CLI commands should use
the properties on TFCClient (client.projects, client.workspaces) rather than
directly instantiating API classes (ProjectAPI(client), WorkspaceAPI(client)).

This matters because:
- Tests that patch TFCClient should only need to patch client.<resource> properties
- No need to separately patch ProjectAPI, WorkspaceAPI constructors
- Single patch point for all tests
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch, PropertyMock

from terrapyne.cli.main import app
from terrapyne.models.project import Project

runner = CliRunner()


# ============================================================================
# Test: project show uses client.projects property
# ============================================================================


def test_show_project_via_client_property(project_detail_response):
    """Test that project show command uses client.projects property instead of ProjectAPI(client)."""
    project = Project.from_api_response(project_detail_response["data"])
    
    # Create a mock TFCClient
    mock_client = MagicMock()
    
    # Mock the projects property (not ProjectAPI class directly)
    mock_projects = MagicMock()
    type(mock_client).projects = PropertyMock(return_value=mock_projects)
    mock_projects.get_by_name.return_value = project
    
    # Mock workspaces property for list operation
    mock_workspaces = MagicMock()
    type(mock_client).workspaces = PropertyMock(return_value=mock_workspaces)
    mock_workspaces.list.return_value = (iter([]), 0)
    
    # Patch TFCClient constructor and resolve_project_context
    with patch("terrapyne.cli.project_cmd.TFCClient") as mock_tfc_client_class, \
         patch("terrapyne.cli.project_cmd.resolve_project_context") as mock_resolve:
        mock_tfc_client_class.return_value.__enter__ = lambda self: mock_client
        mock_tfc_client_class.return_value.__exit__ = lambda self, *args: None
        
        mock_resolve.return_value = ("test-org", project)
        
        result = runner.invoke(
            app,
            ["project", "show", "my-project", "--organization", "test-org"],
        )
        
        # Verify command succeeded
        assert result.exit_code == 0, \
            f"Command failed: {result.stdout}"
        
        # Verify that client.workspaces property was accessed
        # This will fail if the command is still using WorkspaceAPI(client)
        assert mock_workspaces.list.called, \
            "client.workspaces.list() was not called. Did you replace WorkspaceAPI(client) with client.workspaces?"


def test_teams_via_client_property(project_detail_response, team_project_access_response):
    """Test that project teams command uses client.projects property."""
    project = Project.from_api_response(project_detail_response["data"])
    
    # Create a mock TFCClient
    mock_client = MagicMock()
    
    # Mock the projects property
    mock_projects = MagicMock()
    type(mock_client).projects = PropertyMock(return_value=mock_projects)
    mock_projects.get_by_name.return_value = project
    mock_projects.list_team_access.return_value = []
    
    # Context manager support
    mock_client.__enter__ = lambda self: self
    mock_client.__exit__ = lambda self, *args: None
    
    # Patch only TFCClient constructor (not resolve_project_context)
    # This allows resolve_project_context to use client.projects
    with patch("terrapyne.cli.project_cmd.TFCClient") as mock_tfc_client_class:
        mock_tfc_client_class.return_value = mock_client
        
        result = runner.invoke(
            app,
            ["project", "teams", "my-project", "--organization", "test-org"],
        )
        
        # Verify command succeeded
        if result.exit_code != 0:
            print(f"Command output: {result.stdout}")
            print(f"Command stderr: {result.stderr if hasattr(result, 'stderr') else 'N/A'}")
        assert result.exit_code == 0, \
            f"Command failed: {result.stdout}"
        
        # Verify that client.projects.list_team_access was called
        assert mock_projects.list_team_access.called, \
            "client.projects.list_team_access() was not called. Did you replace ProjectAPI(client) with client.projects?"


def test_list_projects_via_client_property(project_list_response):
    """Test that project list command uses client.projects property."""
    projects = [Project.from_api_response(data) for data in project_list_response["data"]]
    
    # Create a mock TFCClient
    mock_client = MagicMock()
    
    # Mock the projects property
    mock_projects = MagicMock()
    type(mock_client).projects = PropertyMock(return_value=mock_projects)
    mock_projects.list.return_value = (iter(projects), len(projects))
    mock_projects.get_workspace_counts.return_value = {}
    
    # Patch only TFCClient constructor, not ProjectAPI
    with patch("terrapyne.cli.project_cmd.TFCClient") as mock_tfc_client_class:
        mock_tfc_client_class.return_value = mock_client
        
        result = runner.invoke(
            app,
            ["project", "list", "--organization", "test-org"],
        )
        
        # Verify command succeeded
        assert result.exit_code == 0, \
            f"Command failed: {result.stdout}"
        
        # Verify that client.projects.list was called
        assert mock_projects.list.called, \
            "client.projects.list() was not called. Did you replace ProjectAPI(client) with client.projects?"


def test_vcs_list_via_client_property():
    """Test that vcs list command uses client.vcs property."""
    # Create a mock TFCClient
    mock_client = MagicMock()
    
    # Mock the vcs property
    mock_vcs = MagicMock()
    type(mock_client).vcs = PropertyMock(return_value=mock_vcs)
    mock_vcs.list_repositories.return_value = []
    
    # Patch TFCClient constructor
    with patch("terrapyne.cli.vcs_cmd.TFCClient") as mock_tfc_client_class:
        mock_tfc_client_class.return_value.__enter__.return_value = mock_client
        mock_tfc_client_class.return_value.__exit__.return_value = None
        
        result = runner.invoke(
            app,
            ["vcs", "repos", "--organization", "test-org"],
        )
        
        # Verify command succeeded
        if result.exit_code != 0:
            print(f"VCS repos failed with exit code {result.exit_code}")
            print(f"STDOUT: {result.stdout}")
            if hasattr(result, "stderr"):
                print(f"STDERR: {result.stderr}")

        assert result.exit_code == 0, \
            f"Command failed: {result.stdout}"
        
        # Verify that client.vcs.list_repositories was called
        assert mock_vcs.list_repositories.called, \
            "client.vcs.list_repositories() was not called. Did you replace VCSAPI(client) with client.vcs?"


def test_workspace_clone_via_client_property():
    """Test that workspace clone command uses client.workspace_clone property."""
    # Create a mock TFCClient
    mock_client = MagicMock()
    
    # Mock the workspace_clone property
    mock_clone = MagicMock()
    type(mock_client).workspace_clone = PropertyMock(return_value=mock_clone)
    mock_clone.clone.return_value = {
        "status": "success", 
        "message": "Cloned!",
        "target_workspace_id": "ws-target",
        "results": {"variables": None, "vcs": None}
    }
    
    # Patch TFCClient constructor
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_tfc_client_class:
        mock_tfc_client_class.return_value.__enter__.return_value = mock_client
        mock_tfc_client_class.return_value.__exit__.return_value = None
        
        result = runner.invoke(
            app,
            ["workspace", "clone", "source", "target", "--organization", "test-org"],
        )
        
        # Verify command succeeded
        if result.exit_code != 0:
            print(f"Workspace clone failed with exit code {result.exit_code}")
            print(f"STDOUT: {result.stdout}")

        assert result.exit_code == 0, \
            f"Command failed: {result.stdout}"
        
        # Verify that client.workspace_clone.clone was called
        assert mock_clone.clone.called, \
            "client.workspace_clone.clone() was not called. Did you replace CloneWorkspaceAPI(client) with client.workspace_clone?"
