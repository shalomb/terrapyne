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
