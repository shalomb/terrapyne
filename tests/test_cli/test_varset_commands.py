"""CLI tests for varset commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.varset import VariableSet, VariableSetVariable

runner = CliRunner()
runner.mix_stderr = True
runner.mix_stderr = True


def _make_varset(id="varset-xyz789", name="shared-aws-creds", global_=False):
    return VariableSet.model_construct(
        id=id,
        name=name,
        description="Shared AWS credentials",
        global_=global_,
        var_count=2,
        workspace_count=3,
    )


def _make_var(id="var-abc123", key="AWS_REGION", value="eu-west-1", sensitive=False):
    return VariableSetVariable.model_construct(
        id=id,
        key=key,
        value=value,
        description=None,
        category="env",
        hcl=False,
        sensitive=sensitive,
    )


class TestVarsetListCommand:
    def _invoke(self, mock_client):
        with (
            patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
            patch("terrapyne.api.client.TFCClient") as mock_tfc,
        ):
            mock_org.return_value = "test-org"
            mock_tfc.return_value.__enter__.return_value = mock_client
            return runner.invoke(app, ["varset", "list", "-o", "test-org"])

    def test_list_exits_zero(self):
        mock_client = MagicMock()
        mock_client.varsets.list.return_value = ([_make_varset()], 1)
        result = self._invoke(mock_client)
        assert result.exit_code == 0

    def test_list_shows_varset_name(self):
        mock_client = MagicMock()
        mock_client.varsets.list.return_value = ([_make_varset(name="shared-aws-creds")], 1)
        result = self._invoke(mock_client)
        assert "shared-aws-creds" in result.output

    def test_list_json_output(self):
        import json

        mock_client = MagicMock()
        mock_client.varsets.list.return_value = ([_make_varset()], 1)
        with (
            patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
            patch("terrapyne.api.client.TFCClient") as mock_tfc,
        ):
            mock_org.return_value = "test-org"
            mock_tfc.return_value.__enter__.return_value = mock_client
            result = runner.invoke(app, ["varset", "list", "-o", "test-org", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["name"] == "shared-aws-creds"


class TestVarsetShowCommand:
    def _invoke(self, mock_client, name="shared-aws-creds"):
        with (
            patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
            patch("terrapyne.api.client.TFCClient") as mock_tfc,
        ):
            mock_org.return_value = "test-org"
            mock_tfc.return_value.__enter__.return_value = mock_client
            return runner.invoke(app, ["varset", "show", name, "-o", "test-org"])

    def test_show_exits_zero(self):
        mock_client = MagicMock()
        mock_client.varsets.get_by_name.return_value = _make_varset()
        mock_client.varsets.get_variables.return_value = iter([_make_var()])
        result = self._invoke(mock_client)
        assert result.exit_code == 0

    def test_show_displays_variable_key(self):
        mock_client = MagicMock()
        mock_client.varsets.get_by_name.return_value = _make_varset()
        mock_client.varsets.get_variables.return_value = iter([_make_var(key="AWS_REGION")])
        result = self._invoke(mock_client)
        assert "AWS_REGION" in result.output

    def test_show_masks_sensitive_variables(self):
        mock_client = MagicMock()
        mock_client.varsets.get_by_name.return_value = _make_varset()
        mock_client.varsets.get_variables.return_value = iter(
            [_make_var(key="SECRET_KEY", value="s3cr3t", sensitive=True)]
        )
        result = self._invoke(mock_client)
        assert "s3cr3t" not in result.output
        assert "••••••••" in result.output

    def test_show_not_found_exits_nonzero(self):
        mock_client = MagicMock()
        mock_client.varsets.get_by_name.side_effect = ValueError("not found")
        result = self._invoke(mock_client, name="missing")
        assert result.exit_code != 0


class TestVarsetApplyCommand:
    def _invoke(self, mock_client, varset="shared-aws-creds", workspace="my-ws"):
        with (
            patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
            patch("terrapyne.api.client.TFCClient") as mock_tfc,
        ):
            mock_org.return_value = "test-org"
            mock_tfc.return_value.__enter__.return_value = mock_client
            return runner.invoke(
                app, ["varset", "apply", varset, "--workspace", workspace, "-o", "test-org"]
            )

    def test_apply_exits_zero(self):
        mock_client = MagicMock()
        mock_client.varsets.get_by_name.return_value = _make_varset()
        mock_client.workspaces.get.return_value = MagicMock(id="ws-abc123")
        mock_client.varsets.apply.return_value = None
        result = self._invoke(mock_client)
        assert result.exit_code == 0

    def test_apply_calls_api_with_ids(self):
        mock_client = MagicMock()
        vs = _make_varset(id="varset-xyz789")
        ws = MagicMock(id="ws-abc123")
        mock_client.varsets.get_by_name.return_value = vs
        mock_client.workspaces.get.return_value = ws
        self._invoke(mock_client)
        mock_client.varsets.apply.assert_called_once_with("varset-xyz789", "ws-abc123")


class TestVarsetRemoveCommand:
    def _invoke(self, mock_client, varset="shared-aws-creds", workspace="my-ws"):
        with (
            patch("terrapyne.cli.context_helpers.resolve_organization") as mock_org,
            patch("terrapyne.api.client.TFCClient") as mock_tfc,
        ):
            mock_org.return_value = "test-org"
            mock_tfc.return_value.__enter__.return_value = mock_client
            return runner.invoke(
                app, ["varset", "remove", varset, "--workspace", workspace, "-o", "test-org"]
            )

    def test_remove_exits_zero(self):
        mock_client = MagicMock()
        mock_client.varsets.get_by_name.return_value = _make_varset()
        mock_client.workspaces.get.return_value = MagicMock(id="ws-abc123")
        mock_client.varsets.remove.return_value = None
        result = self._invoke(mock_client)
        assert result.exit_code == 0

    def test_remove_calls_api_with_ids(self):
        mock_client = MagicMock()
        vs = _make_varset(id="varset-xyz789")
        ws = MagicMock(id="ws-abc123")
        mock_client.varsets.get_by_name.return_value = vs
        mock_client.workspaces.get.return_value = ws
        self._invoke(mock_client)
        mock_client.varsets.remove.assert_called_once_with("varset-xyz789", "ws-abc123")
