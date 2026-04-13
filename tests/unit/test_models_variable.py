"""Unit tests for Variable model."""

from terrapyne.models.variable import WorkspaceVariable


class TestWorkspaceVariableModel:
    """Test WorkspaceVariable model."""

    def test_workspace_variable_from_api_response(self):
        """Test creating WorkspaceVariable from API response."""
        api_response = {
            "id": "var-123",
            "type": "vars",
            "attributes": {
                "key": "environment",
                "value": "production",
                "description": "Environment type",
                "category": "env",
                "sensitive": False,
                "hcl": False,
            },
        }

        var = WorkspaceVariable.from_api_response(api_response)

        assert var.id == "var-123"
        assert var.key == "environment"
        assert var.value == "production"
        assert var.description == "Environment type"
        assert var.category == "env"
        assert var.sensitive is False
        assert var.hcl is False

    def test_workspace_variable_sensitive(self):
        """Test WorkspaceVariable with sensitive flag."""
        api_response = {
            "id": "var-456",
            "type": "vars",
            "attributes": {
                "key": "api_key",
                "value": "secret-value",
                "category": "env",
                "sensitive": True,
                "hcl": False,
            },
        }

        var = WorkspaceVariable.from_api_response(api_response)

        assert var.sensitive is True
        assert var.key == "api_key"

    def test_workspace_variable_hcl(self):
        """Test WorkspaceVariable with HCL value."""
        api_response = {
            "id": "var-789",
            "type": "vars",
            "attributes": {
                "key": "complex_var",
                "value": '{"key": "value"}',
                "category": "terraform",
                "sensitive": False,
                "hcl": True,
            },
        }

        var = WorkspaceVariable.from_api_response(api_response)

        assert var.hcl is True
        assert var.category == "terraform"

    def test_workspace_variable_display_value_masked(self):
        """Test display_value property masks sensitive variables."""
        api_response = {
            "id": "var-secret",
            "type": "vars",
            "attributes": {
                "key": "db_password",
                "value": "super-secret-password",
                "category": "env",
                "sensitive": True,
                "hcl": False,
            },
        }

        var = WorkspaceVariable.from_api_response(api_response)

        assert var.display_value == "••••••••"
        assert var.value == "super-secret-password"  # actual value unchanged

    def test_workspace_variable_display_value_visible(self):
        """Test display_value property shows non-sensitive values."""
        api_response = {
            "id": "var-visible",
            "type": "vars",
            "attributes": {
                "key": "app_name",
                "value": "my-app",
                "category": "env",
                "sensitive": False,
                "hcl": False,
            },
        }

        var = WorkspaceVariable.from_api_response(api_response)

        assert var.display_value == "my-app"

    def test_workspace_variable_is_env_var(self):
        """Test is_env_var property."""
        api_response = {
            "id": "var-env",
            "type": "vars",
            "attributes": {
                "key": "path",
                "value": "/usr/bin",
                "category": "env",
                "sensitive": False,
                "hcl": False,
            },
        }

        var = WorkspaceVariable.from_api_response(api_response)

        assert var.is_env_var is True
        assert var.is_terraform_var is False

    def test_workspace_variable_is_terraform_var(self):
        """Test is_terraform_var property."""
        api_response = {
            "id": "var-tf",
            "type": "vars",
            "attributes": {
                "key": "instance_count",
                "value": "3",
                "category": "terraform",
                "sensitive": False,
                "hcl": False,
            },
        }

        var = WorkspaceVariable.from_api_response(api_response)

        assert var.is_terraform_var is True
        assert var.is_env_var is False
