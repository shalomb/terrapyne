"""Tests for VarSetAPI methods."""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.varsets import VarSetAPI
from terrapyne.models.varset import VariableSet, VariableSetVariable


def _varset_item(id="varset-xyz789", name="shared-aws-creds", global_=False):
    return {
        "id": id,
        "type": "varsets",
        "attributes": {
            "name": name,
            "description": "Shared AWS credentials",
            "global": global_,
            "var-count": 2,
            "workspace-count": 3,
        },
    }


def _var_item(id="var-abc123", key="AWS_REGION", value="eu-west-1"):
    return {
        "id": id,
        "type": "vars",
        "attributes": {
            "key": key,
            "value": value,
            "description": None,
            "category": "env",
            "hcl": False,
            "sensitive": False,
        },
    }


class TestVarSetAPIList:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_organization.return_value = "my-org"
        return client

    @pytest.fixture
    def api(self, mock_client):
        return VarSetAPI(mock_client)

    def test_list_calls_correct_path(self, api, mock_client):
        mock_client.paginate.return_value = (
            MagicMock(items=[_varset_item()], included=[]),
            1,
        )
        _varsets, _count = api.list()
        mock_client.paginate.assert_called_once()
        path = mock_client.paginate.call_args[0][0]
        assert "/organizations/my-org/varsets" in path

    def test_list_returns_varset_instances(self, api, mock_client):
        item = _varset_item()
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([item]))
        result.included = []
        mock_client.paginate.return_value = (result, 1)
        varsets, _count = api.list()
        vs_list = list(varsets)
        assert len(vs_list) == 1
        assert isinstance(vs_list[0], VariableSet)
        assert vs_list[0].name == "shared-aws-creds"

    def test_list_returns_total_count(self, api, mock_client):
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([]))
        result.included = []
        mock_client.paginate.return_value = (result, 42)
        _, count = api.list()
        assert count == 42


class TestVarSetAPIGet:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_organization.return_value = "my-org"
        return client

    @pytest.fixture
    def api(self, mock_client):
        return VarSetAPI(mock_client)

    def test_get_by_name_returns_matching_varset(self, api, mock_client):
        item = _varset_item(name="shared-aws-creds")
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([item]))
        result.included = []
        mock_client.paginate.return_value = (result, 1)
        vs = api.get_by_name("shared-aws-creds")
        assert vs.name == "shared-aws-creds"

    def test_get_by_name_raises_when_not_found(self, api, mock_client):
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([]))
        result.included = []
        mock_client.paginate.return_value = (result, 0)
        with pytest.raises(ValueError, match="not found"):
            api.get_by_name("nonexistent")

    def test_get_variables_calls_correct_path(self, api, mock_client):
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([_var_item()]))
        result.included = []
        mock_client.paginate.return_value = (result, 1)
        list(api.get_variables("varset-xyz789"))
        mock_client.paginate.assert_called_once()
        path = mock_client.paginate.call_args[0][0]
        assert "/varsets/varset-xyz789/relationships/vars" in path

    def test_get_variables_returns_varsetvariable_instances(self, api, mock_client):
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([_var_item()]))
        result.included = []
        mock_client.paginate.return_value = (result, 1)
        variables = list(api.get_variables("varset-xyz789"))
        assert len(variables) == 1
        assert isinstance(variables[0], VariableSetVariable)
        assert variables[0].key == "AWS_REGION"


class TestVarSetAPIApplyRemove:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        return client

    @pytest.fixture
    def api(self, mock_client):
        return VarSetAPI(mock_client)

    def test_apply_posts_to_correct_path(self, api, mock_client):
        api.apply("varset-xyz789", "ws-abc123")
        mock_client.post.assert_called_once()
        path = mock_client.post.call_args[0][0]
        assert "/varsets/varset-xyz789/relationships/workspaces" in path

    def test_apply_sends_correct_payload(self, api, mock_client):
        api.apply("varset-xyz789", "ws-abc123")
        payload = mock_client.post.call_args[1]["json_data"]
        assert payload == {"data": [{"type": "workspaces", "id": "ws-abc123"}]}

    def test_remove_deletes_correct_path(self, api, mock_client):
        api.remove("varset-xyz789", "ws-abc123")
        mock_client.delete.assert_called_once()
        path = mock_client.delete.call_args[0][0]
        assert "/varsets/varset-xyz789/relationships/workspaces" in path

    def test_remove_sends_correct_payload(self, api, mock_client):
        api.remove("varset-xyz789", "ws-abc123")
        payload = mock_client.delete.call_args[1]["json_data"]
        assert payload == {"data": [{"type": "workspaces", "id": "ws-abc123"}]}
