"""Integration tests for workspace clone operations.

Tests the CloneWorkspaceAPI class end-to-end with realistic API mocking
and comprehensive scenario coverage.
"""

import pytest
from unittest.mock import MagicMock, patch

from terrapyne.api.client import TFCClient
from terrapyne.api.workspace_clone import (
    CloneWorkspaceAPI,
    WorkspaceAlreadyExistsError,
    WorkspaceNotFoundError,
    VCSTokenRequiredError,
)
from terrapyne.models.workspace import Workspace
from terrapyne.models.variable import WorkspaceVariable


# ============================================================================
# Workspace Clone Creation Tests
# ============================================================================


class TestCloneWorkspaceCreation:
    """Test workspace creation during clone operation."""

    def test_create_workspace_basic(self, api, mock_client):
        """Test creating workspace with basic settings."""
        mock_client.post.return_value = {
            "data": {
                "id": "ws-created123",
                "type": "workspaces",
                "attributes": {
                    "name": "staging-app",
                    "terraform-version": "1.5.0",
                    "execution-mode": "remote",
                    "auto-apply": False,
                },
            }
        }

        result = api.create_workspace(
            workspace_name="staging-app",
            organization="test-org",
            terraform_version="1.5.0",
            execution_mode="remote",
            auto_apply=False,
        )

        assert result.id == "ws-created123"
        assert result.name == "staging-app"
        assert result.terraform_version == "1.5.0"

        # Verify API was called with correct payload
        call_args = mock_client.post.call_args
        assert call_args is not None
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["name"] == "staging-app"
        assert payload["data"]["attributes"]["terraform-version"] == "1.5.0"

    def test_create_workspace_with_tags(self, api, mock_client):
        """Test creating workspace with tags."""
        mock_client.post.return_value = {
            "data": {
                "id": "ws-tagged123",
                "type": "workspaces",
                "attributes": {
                    "name": "production",
                    "tag-names": ["prod", "backend"],
                },
            }
        }

        result = api.create_workspace(
            workspace_name="production",
            organization="test-org",
            tags=["prod", "backend"],
        )

        assert result.name == "production"
        assert result.tag_names == ["prod", "backend"]

    def test_create_workspace_minimal(self, api, mock_client):
        """Test creating workspace with minimal settings."""
        mock_client.post.return_value = {
            "data": {
                "id": "ws-minimal123",
                "type": "workspaces",
                "attributes": {
                    "name": "basic",
                },
            }
        }

        result = api.create_workspace(
            workspace_name="basic",
            organization="test-org",
        )

        assert result.name == "basic"


# ============================================================================
# Variable Cloning Tests
# ============================================================================


class TestCloneVariablesIntegration:
    """Test variable cloning workflow."""

    def test_get_and_clone_variables(self, api, mock_client):
        """Test retrieving and cloning variables."""
        # Mock get_workspace_variables
        source_vars = [
            {
                "id": "var-1",
                "type": "vars",
                "attributes": {
                    "key": "environment",
                    "value": "prod",
                    "category": "terraform",
                    "sensitive": False,
                    "hcl": False,
                },
            },
            {
                "id": "var-2",
                "type": "vars",
                "attributes": {
                    "key": "db_password",
                    "value": "secret",
                    "category": "env",
                    "sensitive": True,
                    "hcl": False,
                },
            },
        ]

        # paginate_with_meta returns (iterator, total_count) with raw API dicts
        # The get_workspace_variables wraps each with from_api_response
        mock_client.paginate_with_meta.return_value = (
            iter(source_vars),  # Raw API response dicts
            2,
        )

        # Mock variable creation response (wrapped in data)
        mock_client.post.return_value = {"data": source_vars[0]}

        result = api.clone_variables(
            source_workspace_id="ws-source-123",
            target_workspace_id="ws-target-456",
        )

        assert result["status"] == "success"
        assert result["variables_cloned"] == 2
        assert result["terraform_variables"] == 1
        assert result["env_variables"] == 1

    def test_clone_variables_preserves_sensitivity(self, api, mock_client):
        """Test that sensitive flags are preserved during cloning."""
        variables = [
            {
                "id": "var-1",
                "type": "vars",
                "attributes": {
                    "key": "normal_var",
                    "value": "value1",
                    "category": "terraform",
                    "sensitive": False,
                    "hcl": False,
                },
            },
            {
                "id": "var-2",
                "type": "vars",
                "attributes": {
                    "key": "secret_var",
                    "value": "***",
                    "category": "terraform",
                    "sensitive": True,
                    "hcl": False,
                },
            },
        ]

        # paginate_with_meta returns raw API dicts
        mock_client.paginate_with_meta.return_value = (
            iter(variables),  # Raw API dicts, not parsed objects
            2,
        )

        mock_client.post.return_value = {"data": variables[0]}

        result = api.clone_variables(
            source_workspace_id="ws-source-123",
            target_workspace_id="ws-target-456",
        )

        assert result["status"] == "success"
        # Verify post was called twice with correct sensitive flags
        assert mock_client.post.call_count == 2

    def test_clone_empty_variables(self, api, mock_client):
        """Test cloning workspace with no variables."""
        # Return empty iterator when no variables
        mock_client.paginate_with_meta.return_value = (iter([]), 0)

        result = api.clone_variables(
            source_workspace_id="ws-source-123",
            target_workspace_id="ws-target-456",
        )

        assert result["status"] == "success"
        assert result["variables_cloned"] == 0

    def test_clone_variables_error_handling(self, api, mock_client):
        """Test error handling during variable cloning."""
        # Return raw API dict
        mock_client.paginate_with_meta.return_value = (
            iter(
                [
                    {
                        "id": "var-1",
                        "type": "vars",
                        "attributes": {
                            "key": "test",
                            "value": "value",
                            "category": "terraform",
                            "sensitive": False,
                            "hcl": False,
                        },
                    }
                ]
            ),
            1,
        )

        # Make post fail
        mock_client.post.side_effect = Exception("API error")

        result = api.clone_variables(
            source_workspace_id="ws-source-123",
            target_workspace_id="ws-target-456",
        )

        assert result["status"] == "error"
        assert "variables_cloned" in result


# ============================================================================
# VCS Configuration Cloning Tests
# ============================================================================


class TestCloneVCSIntegration:
    """Test VCS configuration cloning workflow."""

    def test_clone_vcs_same_organization(self, api, mock_client):
        """Test cloning VCS config within same organization."""
        # Mock get_workspace_vcs_config
        source_vcs = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {
                "name": "source",
                "vcs-repo": {
                    "identifier": "github.com/acme/terraform",
                    "branch": "main",
                    "oauth-token-id": "ot-123",
                },
            },
        }

        mock_client.get.return_value = {"data": source_vcs}
        mock_client.patch.return_value = {
            "data": {
                "id": "ws-target-456",
                "type": "workspaces",
            }
        }

        result = api.clone_vcs_configuration(
            source_workspace_id="ws-source-123",
            target_workspace_id="ws-target-456",
            source_organization="test-org",
            target_organization="test-org",
        )

        assert result["status"] == "success"
        assert result["vcs_cloned"] is True
        assert result["identifier"] == "github.com/acme/terraform"
        assert result["branch"] == "main"

    def test_clone_vcs_cross_organization(self, api, mock_client):
        """Test cloning VCS config across organizations requires explicit token."""
        source_vcs = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {
                "name": "source",
                "vcs-repo": {
                    "identifier": "github.com/acme/terraform",
                    "branch": "main",
                    "oauth-token-id": "ot-123",
                },
            },
        }

        mock_client.get.return_value = {"data": source_vcs}
        mock_client.patch.return_value = {
            "data": {
                "id": "ws-target-456",
                "type": "workspaces",
            }
        }

        result = api.clone_vcs_configuration(
            source_workspace_id="ws-source-123",
            target_workspace_id="ws-target-456",
            source_organization="org1",
            target_organization="org2",
            vcs_oauth_token_id="ot-neworg",
        )

        assert result["status"] == "success"
        assert result["vcs_cloned"] is True

    def test_clone_vcs_cross_organization_without_token(self, api, mock_client):
        """Test cross-org clone fails without explicit token."""
        source_vcs = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {
                "name": "source",
                "vcs-repo": {
                    "identifier": "github.com/acme/terraform",
                    "branch": "main",
                },
            },
        }

        mock_client.get.return_value = {"data": source_vcs}

        with pytest.raises(VCSTokenRequiredError):
            api.clone_vcs_configuration(
                source_workspace_id="ws-source-123",
                target_workspace_id="ws-target-456",
                source_organization="org1",
                target_organization="org2",
                vcs_oauth_token_id=None,
            )

    def test_clone_vcs_no_source_config(self, api, mock_client):
        """Test gracefully handle source with no VCS config."""
        # Mock workspace without VCS
        source_ws = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {
                "name": "source",
            },
        }

        mock_client.get.return_value = {"data": source_ws}

        result = api.clone_vcs_configuration(
            source_workspace_id="ws-source-123",
            target_workspace_id="ws-target-456",
            source_organization="test-org",
            target_organization="test-org",
        )

        assert result["status"] == "success"
        assert result["vcs_cloned"] is False
        assert "reason" in result


# ============================================================================
# Full Clone Workflow Tests
# ============================================================================


class TestCloneWorkflowIntegration:
    """Test complete clone workflow end-to-end."""

    def test_full_clone_basic(self, api, mock_client):
        """Test basic clone operation (settings only)."""
        # Mock source workspace get
        source_ws_data = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {
                "name": "prod-app",
                "terraform-version": "1.5.0",
                "execution-mode": "remote",
                "auto-apply": False,
                "tag-names": ["prod"],
            },
        }

        # Mock target workspace creation
        target_ws_data = {
            "id": "ws-target-456",
            "type": "workspaces",
            "attributes": {
                "name": "staging-app",
                "terraform-version": "1.5.0",
                "execution-mode": "remote",
                "auto-apply": False,
                "tag-names": ["prod"],
            },
        }

        # First get is source, second get fails (target doesn't exist yet)
        mock_client.get.side_effect = [
            {"data": source_ws_data},
            Exception("404 not found"),  # Target doesn't exist
        ]
        mock_client.post.return_value = {"data": target_ws_data}

        result = api.clone(
            source_workspace_name="prod-app",
            target_workspace_name="staging-app",
            organization="test-org",
        )

        assert result["status"] == "success"
        assert result["source_workspace_name"] == "prod-app"
        assert result["target_workspace_name"] == "staging-app"

    def test_full_clone_with_all_options(self, api, mock_client):
        """Test clone with variables and VCS."""
        source_ws_data = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {
                "name": "prod-app",
                "terraform-version": "1.5.0",
                "execution-mode": "remote",
                "auto-apply": False,
                "vcs-repo": {
                    "identifier": "github.com/acme/terraform",
                    "branch": "main",
                },
            },
        }

        target_ws_data = {
            "id": "ws-target-456",
            "type": "workspaces",
            "attributes": {
                "name": "staging-app",
                "terraform-version": "1.5.0",
            },
        }

        # First get is source, second get fails (target doesn't exist), third get is for VCS
        mock_client.get.side_effect = [
            {"data": source_ws_data},
            Exception("404 not found"),  # Target doesn't exist
            {"data": source_ws_data},  # VCS config fetch
        ]
        mock_client.post.return_value = {"data": target_ws_data}

        # Mock variables
        variables = [
            {
                "id": "var-1",
                "type": "vars",
                "attributes": {
                    "key": "env",
                    "value": "prod",
                    "category": "terraform",
                    "sensitive": False,
                    "hcl": False,
                },
            }
        ]
        mock_client.paginate_with_meta.return_value = (
            iter(variables),  # Raw API dicts
            1,
        )

        result = api.clone(
            source_workspace_name="prod-app",
            target_workspace_name="staging-app",
            organization="test-org",
            with_variables=True,
            with_vcs=True,
        )

        assert result["status"] == "success"
        assert result["results"]["variables"] is not None
        assert result["results"]["variables"]["status"] == "success"
        assert result["results"]["variables"]["variables_cloned"] == 1
        assert result["results"]["vcs"] is not None

    def test_full_clone_source_not_found(self, api, mock_client):
        """Test clone fails when source workspace not found."""
        from terrapyne.api.workspace_clone import WorkspaceNotFoundError
        
        # Mock 404 response for source lookup
        mock_client.get.side_effect = Exception("404 not found")

        with pytest.raises(WorkspaceNotFoundError):
            api.clone(
                source_workspace_name="non-existent",
                target_workspace_name="target",
                organization="test-org",
            )

    def test_full_clone_target_exists_without_force(self, api, mock_client):
        """Test clone fails when target exists without force flag."""
        source_ws_data = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {"name": "prod-app"},
        }

        existing_target_data = {
            "id": "ws-existing-456",
            "type": "workspaces",
            "attributes": {"name": "staging-app"},
        }

        from terrapyne.api.workspace_clone import WorkspaceAlreadyExistsError
        
        # First get is source, second get is target (exists and force=False)
        mock_client.get.side_effect = [{"data": source_ws_data}, {"data": existing_target_data}]

        with pytest.raises(WorkspaceAlreadyExistsError) as exc_info:
            api.clone(
                source_workspace_name="prod-app",
                target_workspace_name="staging-app",
                organization="test-org",
                force=False,
            )

        error_str = str(exc_info.value).lower()
        assert "exists" in error_str or "already" in error_str

    def test_full_clone_target_exists_with_force(self, api, mock_client):
        """Test clone succeeds with force flag when target exists."""
        source_ws_data = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {
                "name": "prod-app",
                "terraform-version": "1.5.0",
                "execution-mode": "remote",
                "auto-apply": False,
            },
        }

        existing_target_data = {
            "id": "ws-existing-456",
            "type": "workspaces",
            "attributes": {"name": "staging-app"},
        }

        # First get is source, second get is target (exists, but force=True)
        mock_client.get.side_effect = [{"data": source_ws_data}, {"data": existing_target_data}]

        result = api.clone(
            source_workspace_name="prod-app",
            target_workspace_name="staging-app",
            organization="test-org",
            force=True,
        )

        assert result["status"] == "success"
        assert "staging-app" in result["target_workspace_name"]

    def test_full_clone_same_name_fails(self, api, mock_client):
        """Test clone fails when source and target names are the same."""
        # This should fail during validation before any API calls
        # No need to mock get() since validate_clone_args raises immediately
        with pytest.raises(ValueError) as exc_info:
            api.clone(
                source_workspace_name="same-app",
                target_workspace_name="same-app",
                organization="test-org",
            )

        error_lower = str(exc_info.value).lower()
        assert "same" in error_lower or "identical" in error_lower or "different" in error_lower


# ============================================================================
# Validation Tests
# ============================================================================


class TestCloneValidation:
    """Test validation of clone arguments."""

    def test_validate_clone_args_basic(self, api, mock_client):
        """Test basic clone argument validation."""
        from terrapyne.api.workspace_clone import WorkspaceNotFoundError
        
        source_ws = {
            "id": "ws-source-123",
            "type": "workspaces",
            "attributes": {"name": "source"},
        }
        # Mock side effect: first call gets source, second call (target) raises 404
        mock_client.get.side_effect = [
            {"data": source_ws},  # First call: get source workspace
            Exception("404 not found"),  # Second call: target doesn't exist
        ]

        source, target = api.validate_clone_args(
            source_workspace_name="source",
            target_workspace_name="target",
            organization="test-org",
            force=False,
        )

        assert source.name == "source"
        assert target is None  # Target doesn't exist yet

    def test_validate_vcs_clone_args_same_org(self, api, mock_client):
        """Test VCS validation for same organization."""
        token = api.validate_vcs_clone_args(
            source_org="test-org",
            target_org="test-org",
            vcs_oauth_token_id=None,
        )

        assert token is None

    def test_validate_vcs_clone_args_cross_org_with_token(self, api, mock_client):
        """Test VCS validation for cross-org with token."""
        token = api.validate_vcs_clone_args(
            source_org="org1",
            target_org="org2",
            vcs_oauth_token_id="ot-neworg",
        )

        assert token == "ot-neworg"

    def test_validate_vcs_clone_args_cross_org_without_token(self, api, mock_client):
        """Test VCS validation for cross-org without token raises error."""
        with pytest.raises(VCSTokenRequiredError):
            api.validate_vcs_clone_args(
                source_org="org1",
                target_org="org2",
                vcs_oauth_token_id=None,
            )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def api():
    """Create CloneWorkspaceAPI instance with mock client."""
    mock_client = MagicMock(spec=TFCClient)
    return CloneWorkspaceAPI(mock_client)


@pytest.fixture
def mock_client(api):
    """Get the mock client from API instance."""
    return api.client
