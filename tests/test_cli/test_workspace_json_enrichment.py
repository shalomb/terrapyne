"""Tests for workspace show --format json enrichment with VCS and variables."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.vcs import VCSConnection
from terrapyne.models.workspace import Workspace

runner = CliRunner()


@pytest.fixture
def sample_workspace():
    """Create a sample workspace with all enrichment fields."""
    return Workspace.model_construct(
        id="ws-enriched",
        name="my-app-dev",
        terraform_version="1.7.0",
        execution_mode="remote",
        auto_apply=False,
        locked=False,
        created_at="2025-03-01T00:00:00Z",
        updated_at="2025-03-15T10:00:00Z",
        tag_names=["dev", "backend"],
        project_id="prj-abc123",
        project_name="Infrastructure",
        environment="development",
        working_directory="terraform/",
    )


@pytest.fixture
def sample_vcs():
    """Create a sample VCS connection."""
    return VCSConnection.model_validate(
        {
            "identifier": "myorg/my-app",
            "branch": "develop",
            "repository-http-url": "https://github.com/myorg/my-app",
            "oauth-token-id": "ot-abc123",
            "service-provider": "github",
            "working-directory": "terraform/",
        }
    )


@pytest.fixture
def sample_variables():
    """Create sample workspace variables."""
    return [
        WorkspaceVariable.model_construct(
            id="var-1",
            key="region",
            value="us-east-1",
            category="terraform",
            sensitive=False,
        ),
        WorkspaceVariable.model_construct(
            id="var-2",
            key="AWS_ACCESS_KEY_ID",
            value="***",
            category="env",
            sensitive=True,
        ),
        WorkspaceVariable.model_construct(
            id="var-3",
            key="instance_count",
            value="3",
            category="terraform",
            sensitive=False,
        ),
        WorkspaceVariable.model_construct(
            id="var-4",
            key="AWS_SECRET_ACCESS_KEY",
            value="***",
            category="env",
            sensitive=True,
        ),
    ]


class TestWorkspaceShowJSONEnrichment:
    """Test workspace show --format json includes enrichment fields."""

    def _invoke_with_mocks(self, mock_client):
        """Invoke CLI with mocked TFCClient."""
        with (
            patch("terrapyne.cli.utils.validate_context") as v,
            patch("terrapyne.cli.workspace_cmd.TFCClient") as c,
        ):
            v.return_value = ("test-org", "my-app-dev")
            c.return_value.__enter__.return_value = mock_client
            return runner.invoke(
                app, ["workspace", "show", "my-app-dev", "-o", "test-org", "--format", "json"]
            )

    def test_json_includes_vcs_metadata(self, sample_workspace, sample_vcs):
        """Workspace JSON should include VCS metadata: identifier, branch, working_directory, url."""
        mock_client = MagicMock()
        mock_client.workspaces.get.return_value = sample_workspace
        mock_client.runs.list.return_value = ([], 0)
        mock_client.vcs.get_workspace_vcs.return_value = sample_vcs
        mock_client.workspaces.get_variables.return_value = []

        result = self._invoke_with_mocks(mock_client)

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        assert "vcs" in output
        assert output["vcs"]["identifier"] == "myorg/my-app"
        assert output["vcs"]["branch"] == "develop"
        assert output["vcs"]["working_directory"] == "terraform/"
        assert output["vcs"]["repository_url"] == "https://github.com/myorg/my-app"

    def test_json_includes_workspace_enrichment_fields(self, sample_workspace, sample_vcs):
        """Workspace JSON should include enriched fields: updated_at, environment, project_name, working_directory."""
        mock_client = MagicMock()
        mock_client.workspaces.get.return_value = sample_workspace
        mock_client.runs.list.return_value = ([], 0)
        mock_client.vcs.get_workspace_vcs.return_value = sample_vcs
        mock_client.workspaces.get_variables.return_value = []

        result = self._invoke_with_mocks(mock_client)

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        assert output["updated_at"] == "2025-03-15T10:00:00Z"
        assert output["environment"] == "development"
        assert output["project_name"] == "Infrastructure"
        assert output["working_directory"] == "terraform/"

    def test_json_includes_variable_summary(self, sample_workspace, sample_vcs, sample_variables):
        """Workspace JSON should include variable_summary with counts by category and sensitivity."""
        mock_client = MagicMock()
        mock_client.workspaces.get.return_value = sample_workspace
        mock_client.runs.list.return_value = ([], 0)
        mock_client.vcs.get_workspace_vcs.return_value = sample_vcs
        mock_client.workspaces.get_variables.return_value = sample_variables

        result = self._invoke_with_mocks(mock_client)

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        assert "variable_summary" in output
        summary = output["variable_summary"]
        assert summary["total"] == 4
        assert summary["terraform"] == 2
        assert summary["env"] == 2
        assert summary["sensitive"] == 2

    def test_json_handles_no_vcs_gracefully(self, sample_workspace, sample_variables):
        """When workspace has no VCS, JSON should have vcs=null."""
        mock_client = MagicMock()
        mock_client.workspaces.get.return_value = sample_workspace
        mock_client.runs.list.return_value = ([], 0)
        mock_client.vcs.get_workspace_vcs.return_value = None
        mock_client.workspaces.get_variables.return_value = sample_variables

        result = self._invoke_with_mocks(mock_client)

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        assert output["vcs"] is None

    def test_json_handles_no_variables_gracefully(self, sample_workspace, sample_vcs):
        """When workspace has no variables, JSON should have variable_summary=null."""
        mock_client = MagicMock()
        mock_client.workspaces.get.return_value = sample_workspace
        mock_client.runs.list.return_value = ([], 0)
        mock_client.vcs.get_workspace_vcs.return_value = sample_vcs
        mock_client.workspaces.get_variables.return_value = []

        result = self._invoke_with_mocks(mock_client)

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        # Empty list should produce variable_summary with total=0, not None
        assert output["variable_summary"] is None or output["variable_summary"]["total"] == 0

    def test_json_handles_vcs_api_error_gracefully(self, sample_workspace):
        """When VCS API call fails, JSON should still produce valid output with vcs=null."""
        import httpx

        mock_client = MagicMock()
        mock_client.workspaces.get.return_value = sample_workspace
        mock_client.runs.list.return_value = ([], 0)
        mock_client.vcs.get_workspace_vcs.side_effect = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        mock_client.workspaces.get_variables.return_value = []

        result = self._invoke_with_mocks(mock_client)

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        assert output["vcs"] is None

    def test_json_handles_variables_api_error_gracefully(self, sample_workspace, sample_vcs):
        """When variables API call fails, JSON should still produce valid output with variable_summary=null."""
        import httpx

        mock_client = MagicMock()
        mock_client.workspaces.get.return_value = sample_workspace
        mock_client.runs.list.return_value = ([], 0)
        mock_client.vcs.get_workspace_vcs.return_value = sample_vcs
        mock_client.workspaces.get_variables.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=MagicMock(status_code=403)
        )

        result = self._invoke_with_mocks(mock_client)

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        assert output["variable_summary"] is None
        assert output["vcs"] is not None  # VCS should still be present

    def test_json_output_is_valid_json(self, sample_workspace, sample_vcs, sample_variables):
        """JSON output must be valid and parseable."""
        mock_client = MagicMock()
        mock_client.workspaces.get.return_value = sample_workspace
        mock_client.runs.list.return_value = ([], 0)
        mock_client.vcs.get_workspace_vcs.return_value = sample_vcs
        mock_client.workspaces.get_variables.return_value = sample_variables

        result = self._invoke_with_mocks(mock_client)

        assert result.exit_code == 0
        # This will raise if not valid JSON
        output = json.loads(result.stdout)
        assert isinstance(output, dict)
        assert "id" in output
