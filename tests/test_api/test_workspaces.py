"""Tests for WorkspaceAPI methods, especially variable operations."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.workspace import Workspace


class TestWorkspaceVariableOperations:
    """Test variable create and update operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create WorkspaceAPI instance with mock client."""
        return WorkspaceAPI(mock_client)

    @pytest.fixture
    def sample_workspace_id(self):
        """Sample workspace ID for testing."""
        return "ws-abc123"

    @pytest.fixture
    def sample_variable_response(self):
        """Sample TFC API response for a variable."""
        return {
            "id": "var-xyz789",
            "type": "vars",
            "attributes": {
                "key": "environment",
                "value": "production",
                "category": "terraform",
                "hcl": False,
                "sensitive": False,
                "description": "Deployment environment",
            },
        }

    @pytest.fixture
    def sample_sensitive_variable_response(self):
        """Sample response for a sensitive variable."""
        return {
            "id": "var-secret123",
            "type": "vars",
            "attributes": {
                "key": "api_key",
                "value": "sk-abc123xyz",
                "category": "env",
                "hcl": False,
                "sensitive": True,
                "description": None,
            },
        }

    def test_create_variable_basic(self, api, mock_client, sample_workspace_id, sample_variable_response):
        """Test creating a basic terraform variable."""
        mock_client.post.return_value = {"data": sample_variable_response}

        variable = api.create_variable(
            workspace_id=sample_workspace_id,
            key="environment",
            value="production",
        )

        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/vars"

        # Verify payload structure
        payload = call_args[1]["json_data"]
        assert payload["data"]["type"] == "vars"
        assert payload["data"]["attributes"]["key"] == "environment"
        assert payload["data"]["attributes"]["value"] == "production"
        assert payload["data"]["attributes"]["category"] == "terraform"
        assert payload["data"]["relationships"]["workspace"]["data"]["id"] == sample_workspace_id

        # Verify returned variable
        assert isinstance(variable, WorkspaceVariable)
        assert variable.key == "environment"
        assert variable.value == "production"

    def test_create_variable_with_all_options(
        self, api, mock_client, sample_workspace_id, sample_sensitive_variable_response
    ):
        """Test creating a variable with all optional parameters."""
        mock_client.post.return_value = {"data": sample_sensitive_variable_response}

        variable = api.create_variable(
            workspace_id=sample_workspace_id,
            key="api_key",
            value="sk-abc123xyz",
            category="env",
            hcl=False,
            sensitive=True,
            description="API key for external service",
        )

        # Verify API call
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]

        # Verify all attributes
        assert payload["data"]["attributes"]["key"] == "api_key"
        assert payload["data"]["attributes"]["category"] == "env"
        assert payload["data"]["attributes"]["sensitive"] is True
        assert payload["data"]["attributes"]["description"] == "API key for external service"

        # Verify returned variable
        assert variable.key == "api_key"
        assert variable.sensitive is True

    def test_create_variable_hcl(self, api, mock_client, sample_workspace_id):
        """Test creating an HCL-encoded variable."""
        hcl_response = {
            "id": "var-hcl123",
            "type": "vars",
            "attributes": {
                "key": "custom_object",
                "value": '{ "region" = "us-west-2" }',
                "category": "terraform",
                "hcl": True,
                "sensitive": False,
                "description": "Custom HCL object",
            },
        }
        mock_client.post.return_value = {"data": hcl_response}

        variable = api.create_variable(
            workspace_id=sample_workspace_id,
            key="custom_object",
            value='{ "region" = "us-west-2" }',
            hcl=True,
            description="Custom HCL object",
        )

        # Verify HCL flag in payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["hcl"] is True

        # Verify returned variable
        assert variable.hcl is True

    def test_create_variable_without_description(self, api, mock_client, sample_workspace_id):
        """Test that description is optional and not included if None."""
        response = {
            "id": "var-nodesc",
            "type": "vars",
            "attributes": {
                "key": "simple_var",
                "value": "simple_value",
                "category": "terraform",
                "hcl": False,
                "sensitive": False,
            },
        }
        mock_client.post.return_value = {"data": response}

        variable = api.create_variable(
            workspace_id=sample_workspace_id,
            key="simple_var",
            value="simple_value",
        )

        # Verify description is not in payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert "description" not in payload["data"]["attributes"]

        # Verify variable returned correctly
        assert variable.key == "simple_var"

    def test_update_variable_value_only(self, api, mock_client, sample_variable_response):
        """Test updating only the value of a variable."""
        updated_response = {**sample_variable_response}
        updated_response["attributes"]["value"] = "staging"
        mock_client.patch.return_value = {"data": updated_response}

        variable = api.update_variable(
            variable_id="var-xyz789",
            value="staging",
        )

        # Verify API call
        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        assert call_args[0][0] == "/vars/var-xyz789"

        # Verify only value in payload
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"] == {"value": "staging"}

        # Verify returned variable
        assert variable.value == "staging"

    def test_update_variable_multiple_fields(self, api, mock_client):
        """Test updating multiple fields at once."""
        updated_response = {
            "id": "var-test123",
            "type": "vars",
            "attributes": {
                "key": "new_name",
                "value": "new_value",
                "category": "env",
                "hcl": True,
                "sensitive": True,
                "description": "Updated description",
            },
        }
        mock_client.patch.return_value = {"data": updated_response}

        variable = api.update_variable(
            variable_id="var-test123",
            key="new_name",
            value="new_value",
            hcl=True,
            sensitive=True,
            description="Updated description",
        )

        # Verify all fields in payload
        call_args = mock_client.patch.call_args
        payload = call_args[1]["json_data"]
        attributes = payload["data"]["attributes"]
        assert attributes["key"] == "new_name"
        assert attributes["value"] == "new_value"
        assert attributes["hcl"] is True
        assert attributes["sensitive"] is True
        assert attributes["description"] == "Updated description"

        # Verify returned variable
        assert variable.key == "new_name"
        assert variable.hcl is True

    def test_update_variable_no_fields(self, api, mock_client):
        """Test update with no fields - should still work with empty attributes."""
        response = {
            "id": "var-test123",
            "type": "vars",
            "attributes": {
                "key": "unchanged",
                "value": "unchanged",
                "category": "terraform",
                "hcl": False,
                "sensitive": False,
            },
        }
        mock_client.patch.return_value = {"data": response}

        variable = api.update_variable(variable_id="var-test123")

        # Verify payload with empty attributes
        call_args = mock_client.patch.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"] == {}

        # Should still return a variable
        assert variable.key == "unchanged"

    def test_update_variable_sensitive_flag(self, api, mock_client):
        """Test toggling the sensitive flag on a variable."""
        response = {
            "id": "var-xyz789",
            "type": "vars",
            "attributes": {
                "key": "api_secret",
                "value": "secret_value",
                "category": "env",
                "hcl": False,
                "sensitive": True,
                "description": "API secret",
            },
        }
        mock_client.patch.return_value = {"data": response}

        variable = api.update_variable(
            variable_id="var-xyz789",
            sensitive=True,
        )

        # Verify sensitive flag in payload
        call_args = mock_client.patch.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["sensitive"] is True

        # Verify returned variable
        assert variable.sensitive is True

    def test_update_variable_clears_description(self, api, mock_client):
        """Test clearing description by setting it to empty string."""
        response = {
            "id": "var-desc123",
            "type": "vars",
            "attributes": {
                "key": "some_var",
                "value": "some_value",
                "category": "terraform",
                "hcl": False,
                "sensitive": False,
                "description": None,
            },
        }
        mock_client.patch.return_value = {"data": response}

        variable = api.update_variable(
            variable_id="var-desc123",
            description="",
        )

        # Verify empty description in payload
        call_args = mock_client.patch.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["description"] == ""

        # Verify variable has no description
        assert variable.description is None

    def test_create_variable_returns_workspace_variable(self, api, mock_client, sample_workspace_id):
        """Test that create_variable returns a WorkspaceVariable instance."""
        response = {
            "id": "var-123",
            "type": "vars",
            "attributes": {
                "key": "test_key",
                "value": "test_value",
                "category": "terraform",
                "hcl": False,
                "sensitive": False,
            },
        }
        mock_client.post.return_value = {"data": response}

        variable = api.create_variable(
            workspace_id=sample_workspace_id,
            key="test_key",
            value="test_value",
        )

        # Verify return type and properties
        assert isinstance(variable, WorkspaceVariable)
        assert hasattr(variable, "display_value")
        assert hasattr(variable, "is_terraform_var")
        assert variable.is_terraform_var is True


class TestWorkspaceVariableIntegration:
    """Integration tests for variable operations with other methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create WorkspaceAPI instance with mock client."""
        return WorkspaceAPI(mock_client)

    def test_create_and_get_variables_workflow(self, api, mock_client):
        """Test creating a variable and then retrieving it."""
        workspace_id = "ws-test123"

        # Mock create response
        create_response = {
            "id": "var-new123",
            "type": "vars",
            "attributes": {
                "key": "environment",
                "value": "production",
                "category": "terraform",
                "hcl": False,
                "sensitive": False,
                "description": "Environment name",
            },
        }
        mock_client.post.return_value = {"data": create_response}

        # Create variable
        created_var = api.create_variable(
            workspace_id=workspace_id,
            key="environment",
            value="production",
            description="Environment name",
        )

        assert created_var.key == "environment"
        assert created_var.id == "var-new123"

        # Mock get_variables to include the newly created variable
        mock_client.paginate.return_value = iter([create_response])

        # Get variables
        variables = api.get_variables(workspace_id)

        assert len(variables) == 1
        assert variables[0].key == "environment"
        assert variables[0].id == "var-new123"
