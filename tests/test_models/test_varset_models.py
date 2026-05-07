"""Tests for VariableSet and VariableSetVariable models."""

from terrapyne.models.varset import VariableSet, VariableSetVariable


class TestVariableSetVariable:
    """Tests for VariableSetVariable model."""

    def _make_var_response(self, **overrides):
        data = {
            "id": "var-abc123",
            "type": "vars",
            "attributes": {
                "key": "AWS_REGION",
                "value": "eu-west-1",
                "description": "AWS region",
                "category": "env",
                "hcl": False,
                "sensitive": False,
            },
        }
        data["attributes"].update(overrides)
        return data

    def test_from_api_response_populates_fields(self):
        var = VariableSetVariable.from_api_response(self._make_var_response())
        assert var.id == "var-abc123"
        assert var.key == "AWS_REGION"
        assert var.value == "eu-west-1"
        assert var.category == "env"
        assert var.hcl is False
        assert var.sensitive is False

    def test_sensitive_variable_masks_display_value(self):
        var = VariableSetVariable.from_api_response(
            self._make_var_response(sensitive=True, value="secret")
        )
        assert var.display_value == "••••••••"

    def test_non_sensitive_variable_shows_value(self):
        var = VariableSetVariable.from_api_response(self._make_var_response())
        assert var.display_value == "eu-west-1"

    def test_null_value_shows_empty_string(self):
        var = VariableSetVariable.from_api_response(self._make_var_response(value=None))
        assert var.display_value == ""

    def test_category_env_is_env_var(self):
        var = VariableSetVariable.from_api_response(self._make_var_response(category="env"))
        assert var.is_env_var is True
        assert var.is_terraform_var is False

    def test_category_terraform_is_terraform_var(self):
        var = VariableSetVariable.from_api_response(self._make_var_response(category="terraform"))
        assert var.is_terraform_var is True
        assert var.is_env_var is False


class TestVariableSet:
    """Tests for VariableSet model."""

    def _make_varset_response(self, **overrides):
        attrs = {
            "name": "shared-aws-creds",
            "description": "Shared AWS credentials",
            "global": False,
            "var-count": 3,
            "workspace-count": 5,
        }
        attrs.update(overrides)
        return {
            "id": "varset-xyz789",
            "type": "varsets",
            "attributes": attrs,
        }

    def test_from_api_response_populates_fields(self):
        vs = VariableSet.from_api_response(self._make_varset_response())
        assert vs.id == "varset-xyz789"
        assert vs.name == "shared-aws-creds"
        assert vs.description == "Shared AWS credentials"
        assert vs.global_ is False
        assert vs.var_count == 3
        assert vs.workspace_count == 5

    def test_global_varset(self):
        vs = VariableSet.from_api_response(self._make_varset_response(**{"global": True}))
        assert vs.global_ is True

    def test_description_defaults_to_none(self):
        data = self._make_varset_response()
        del data["attributes"]["description"]
        vs = VariableSet.from_api_response(data)
        assert vs.description is None

    def test_model_dump_json_serialisable(self):
        vs = VariableSet.from_api_response(self._make_varset_response())
        d = vs.model_dump()
        assert d["id"] == "varset-xyz789"
        assert "name" in d
