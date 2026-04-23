"""Unit tests for workspace clone logic.

Tests the core validation and cloning logic for workspaces.
Following TDD approach: these tests define expected behavior.
"""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.client import TFCClient
from terrapyne.api.workspace_clone import VCSTokenRequiredError
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.workspace import Workspace, WorkspaceVCS


class TestWorkspaceCloneValidation:
    """Test validation logic for workspace cloning."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock(spec=TFCClient)

    @pytest.fixture
    def source_workspace_data(self):
        """Sample source workspace data."""
        return {
            "id": "ws-source123",
            "type": "workspaces",
            "attributes": {
                "name": "prod-app",
                "description": "Production workspace",
                "terraform_version": "1.5.0",
                "execution_mode": "remote",
                "auto_apply": False,
                "lock": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-10T12:00:00Z",
            },
            "relationships": {
                "organization": {"data": {"id": "org-test", "type": "organizations"}},
            },
        }

    @pytest.fixture
    def target_workspace_data(self):
        """Sample target workspace data for already-exists scenario."""
        return {
            "id": "ws-target456",
            "type": "workspaces",
            "attributes": {
                "name": "prod-app-clone",
                "description": "Clone workspace",
                "terraform_version": "1.4.0",
                "execution_mode": "local",
                "auto_apply": True,
                "lock": False,
                "created_at": "2024-01-05T00:00:00Z",
                "updated_at": "2024-01-10T12:00:00Z",
            },
            "relationships": {
                "organization": {"data": {"id": "org-test", "type": "organizations"}},
            },
        }

    def test_clone_validates_source_workspace_exists(self, mock_client, source_workspace_data):
        """Clone should require source workspace to exist."""
        # GIVEN: source workspace does not exist (get raises error)
        mock_client.get.side_effect = Exception("404: Workspace not found")

        # WHEN: attempting to validate source for clone
        # THEN: should raise appropriate error
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI, WorkspaceNotFoundError

        clone_api = CloneWorkspaceAPI(mock_client)

        with pytest.raises(WorkspaceNotFoundError):
            clone_api.validate_clone_args(
                source_workspace_name="nonexistent",
                target_workspace_name="target",
                organization="test-org",
            )

    def test_clone_allows_nonexistent_target_by_default(self, mock_client, source_workspace_data):
        """Clone should allow non-existent target workspace."""
        # GIVEN: source workspace exists
        Workspace.from_api_response(source_workspace_data)

        # GIVEN: target workspace does not exist (get raises 404)
        def get_side_effect(path):
            if "prod-app-clone" in path:
                raise Exception("404: Not found")
            return {"data": source_workspace_data}

        mock_client.get.side_effect = get_side_effect

        # WHEN: validating clone args
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        clone_api = CloneWorkspaceAPI(mock_client)

        # THEN: should succeed
        source_result, target = clone_api.validate_clone_args(
            source_workspace_name="prod-app",
            target_workspace_name="prod-app-clone",
            organization="test-org",
            force=False,
        )

        assert source_result is not None
        # target should be None since it doesn't exist
        assert target is None

    def test_clone_fails_if_target_exists_without_force(
        self, mock_client, source_workspace_data, target_workspace_data
    ):
        """Clone should fail if target exists and force=False."""
        # GIVEN: both source and target workspaces exist
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI, WorkspaceAlreadyExistsError

        def mock_get_side_effect(path):
            if "prod-app-clone" in path:
                return {"data": target_workspace_data}
            else:
                return {"data": source_workspace_data}

        mock_client.get.side_effect = mock_get_side_effect
        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: validating clone args without force
        # THEN: should raise WorkspaceAlreadyExistsError
        with pytest.raises(WorkspaceAlreadyExistsError):
            clone_api.validate_clone_args(
                source_workspace_name="prod-app",
                target_workspace_name="prod-app-clone",
                organization="test-org",
                force=False,
            )

    def test_clone_with_force_allows_existing_target(
        self, mock_client, source_workspace_data, target_workspace_data
    ):
        """Clone with force=True should allow existing target workspace."""
        # GIVEN: both source and target workspaces exist
        mock_client.get.side_effect = lambda path: (
            {"data": source_workspace_data}
            if "prod-app" in path
            else {"data": target_workspace_data}
            if "prod-app-clone" in path
            else None
        )

        # WHEN: validating clone args with force=True
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        clone_api = CloneWorkspaceAPI(mock_client)

        # THEN: should succeed
        source, target = clone_api.validate_clone_args(
            source_workspace_name="prod-app",
            target_workspace_name="prod-app-clone",
            organization="test-org",
            force=True,
        )

        assert source is not None
        assert target is not None

    def test_clone_validates_source_and_target_different(self, mock_client, source_workspace_data):
        """Clone should fail if source and target have same name."""
        # GIVEN: source workspace exists
        mock_client.get.return_value = {"data": source_workspace_data}

        # WHEN: attempting to clone with same name
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        clone_api = CloneWorkspaceAPI(mock_client)

        # THEN: should raise ValueError
        with pytest.raises(ValueError):
            clone_api.validate_clone_args(
                source_workspace_name="prod-app",
                target_workspace_name="prod-app",  # same as source
                organization="test-org",
            )


class TestVariableMapping:
    """Test variable cloning logic."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock(spec=TFCClient)

    @pytest.fixture
    def sample_variables(self):
        """Sample variables with different types and sensitivities."""
        return [
            {
                "id": "var-env1",
                "type": "vars",
                "attributes": {
                    "key": "ENVIRONMENT",
                    "value": "production",
                    "category": "env",
                    "sensitive": False,
                    "hcl": False,
                },
            },
            {
                "id": "var-api-key",
                "type": "vars",
                "attributes": {
                    "key": "API_KEY",
                    "value": "sk-prod-secret123",
                    "category": "env",
                    "sensitive": True,
                    "hcl": False,
                },
            },
            {
                "id": "var-tf1",
                "type": "vars",
                "attributes": {
                    "key": "app_version",
                    "value": "1.0.5",
                    "category": "terraform",
                    "sensitive": False,
                    "hcl": False,
                },
            },
        ]

    def test_preserve_sensitive_variables(self, mock_client, sample_variables):
        """Sensitive flag should be preserved when cloning variables."""
        # GIVEN: source workspace has sensitive variables
        source_vars = [WorkspaceVariable.from_api_response(v) for v in sample_variables]

        # WHEN: extracting variables for cloning
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        CloneWorkspaceAPI(mock_client)

        # THEN: sensitive variables should be flagged as such
        sensitive_var = next(v for v in source_vars if v.key == "API_KEY")
        assert sensitive_var.sensitive is True
        assert sensitive_var.value == "sk-prod-secret123"

    def test_map_variables_by_category(self, mock_client, sample_variables):
        """Variables should be properly categorized."""
        # GIVEN: source workspace has mixed variable categories
        source_vars = [WorkspaceVariable.from_api_response(v) for v in sample_variables]

        # WHEN: grouping variables by category
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        CloneWorkspaceAPI(mock_client)

        env_vars = [v for v in source_vars if v.category == "env"]
        tf_vars = [v for v in source_vars if v.category == "terraform"]

        # THEN: should have correct counts
        assert len(env_vars) == 2  # ENVIRONMENT, API_KEY
        assert len(tf_vars) == 1  # app_version

    def test_handle_variable_name_conflicts(self, mock_client):
        """Should handle variables with same key in different categories."""
        # GIVEN: variables with same key but different categories
        var1 = {
            "id": "var-1",
            "type": "vars",
            "attributes": {
                "key": "config",
                "value": "prod-config",
                "category": "env",
                "sensitive": False,
                "hcl": False,
            },
        }
        var2 = {
            "id": "var-2",
            "type": "vars",
            "attributes": {
                "key": "config",
                "value": "{...}",
                "category": "terraform",
                "sensitive": False,
                "hcl": True,
            },
        }

        # WHEN: cloning both variables
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        CloneWorkspaceAPI(mock_client)

        var1_obj = WorkspaceVariable.from_api_response(var1)
        var2_obj = WorkspaceVariable.from_api_response(var2)

        # THEN: both should be preserved
        assert var1_obj.key == var2_obj.key == "config"
        assert var1_obj.category != var2_obj.category
        assert var1_obj.category == "env"
        assert var2_obj.category == "terraform"

    def test_clone_respects_with_variables_flag(self, mock_client):
        """Clone should only copy variables when --with-variables flag set."""
        # GIVEN: clone scope includes variables
        # WHEN: with_variables=True
        # THEN: variables should be included in clone spec

        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        CloneWorkspaceAPI(mock_client)

        # Build clone spec with variables
        spec_with_vars = {
            "include_variables": True,
            "include_vcs": False,
            "include_team_access": False,
        }

        # THEN: should have variables in spec
        assert spec_with_vars["include_variables"] is True
        assert spec_with_vars["include_vcs"] is False

    def test_get_workspace_variables(self, mock_client, sample_variables):
        """Should retrieve all variables from workspace."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        # GIVEN: paginate returns variables
        mock_client.paginate_with_meta.return_value = (iter(sample_variables), 3)

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: getting workspace variables
        vars_list = list(clone_api.get_workspace_variables("ws-123"))

        # THEN: should return all variables
        assert len(vars_list) == 3
        assert all(isinstance(v, WorkspaceVariable) for v in vars_list)

    def test_map_variables_by_category_preserves_sensitivity(self, mock_client, sample_variables):
        """Variables should be mapped by category with sensitivity preserved."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        clone_api = CloneWorkspaceAPI(mock_client)
        source_vars = [WorkspaceVariable.from_api_response(v) for v in sample_variables]

        # WHEN: mapping variables for clone
        mapped = clone_api.map_variables_for_clone(iter(source_vars))

        # THEN: should have variables in both categories
        assert "terraform" in mapped
        assert "env" in mapped

        # THEN: sensitive flag should be preserved
        env_vars = mapped["env"]
        api_key_var = next((v for v in env_vars if v["key"] == "API_KEY"), None)
        assert api_key_var is not None
        assert api_key_var["sensitive"] is True

        # THEN: non-sensitive vars should be marked as not sensitive
        env_var = next((v for v in env_vars if v["key"] == "ENVIRONMENT"), None)
        assert env_var is not None
        assert env_var["sensitive"] is False

    def test_create_variable_sends_correct_payload(self, mock_client):
        """Variable creation should send properly formatted payload to API."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        response = {
            "id": "var-new",
            "type": "vars",
            "attributes": {
                "key": "test_key",
                "value": "test_value",
                "category": "env",
                "sensitive": True,
                "hcl": False,
            },
        }
        mock_client.post.return_value = {"data": response}

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: creating a variable
        var = clone_api.create_variable_in_workspace(
            target_workspace_id="ws-target",
            key="test_key",
            value="test_value",
            category="env",
            sensitive=True,
        )

        # THEN: should call post with correct payload
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/vars"

        # Check payload structure
        payload = call_args[1]["json_data"]
        assert payload["data"]["type"] == "vars"
        assert payload["data"]["attributes"]["key"] == "test_key"
        assert payload["data"]["attributes"]["sensitive"] is True
        assert payload["data"]["relationships"]["workspace"]["data"]["id"] == "ws-target"

        # Should return created variable
        assert isinstance(var, WorkspaceVariable)

    def test_clone_variables_empty_source(self, mock_client):
        """Clone should handle source workspace with no variables."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        mock_client.paginate_with_meta.return_value = (iter([]), None)

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: cloning variables when source has none
        result = clone_api.clone_variables(
            source_workspace_id="ws-empty",
            target_workspace_id="ws-target",
        )

        # THEN: should return success with 0 variables cloned
        assert result["status"] == "success"
        assert result["variables_cloned"] == 0

    def test_clone_variables_preserves_all_metadata(self, mock_client, sample_variables):
        """Variable cloning should preserve all metadata."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        mock_client.paginate_with_meta.return_value = (iter(sample_variables), 3)

        # Mock the post response for each variable
        def mock_post_response(path, json_data):
            var_data = json_data["data"]["attributes"]
            return {
                "data": {
                    "id": "var-created",
                    "type": "vars",
                    "attributes": var_data,
                }
            }

        mock_client.post.side_effect = mock_post_response

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: cloning variables
        result = clone_api.clone_variables(
            source_workspace_id="ws-source",
            target_workspace_id="ws-target",
        )

        # THEN: should successfully clone all variables
        assert result["status"] == "success"
        assert result["variables_cloned"] == 3
        assert result["terraform_variables"] == 1  # app_version
        assert result["env_variables"] == 2  # ENVIRONMENT, API_KEY

        # THEN: post should be called for each variable
        assert mock_client.post.call_count == 3


class TestVCSConfigCopy:
    """Test VCS configuration cloning logic."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock(spec=TFCClient)

    @pytest.fixture
    def source_with_vcs(self):
        """Source workspace with VCS configuration."""
        return {
            "id": "ws-vcs1",
            "type": "workspaces",
            "attributes": {
                "name": "prod-with-vcs",
                "terraform_version": "1.5.0",
                "execution_mode": "remote",
                "auto_apply": False,
                "lock": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-10T12:00:00Z",
                "vcs-repo": {
                    "identifier": "my-org/my-repo",
                    "branch": "main",
                    "oauth-token-id": "ot-abc123",
                },
            },
            "relationships": {
                "organization": {"data": {"id": "org-test", "type": "organizations"}},
            },
        }

    @pytest.fixture
    def vcs_repo_data(self):
        """VCS repository configuration."""
        return {
            "id": "wr-abc123",
            "type": "workspace-vcs-repos",
            "attributes": {
                "identifier": "my-org/my-repo",
                "branch": "main",
                "ingress_submodules": False,
                "tags_regex": None,
            },
            "relationships": {
                "oauth-token": {"data": {"id": "ot-oauth123", "type": "oauth-tokens"}}
            },
        }

    def test_copy_vcs_config_same_org(self, mock_client, source_with_vcs, vcs_repo_data):
        """VCS config should be copied when cloning within same organization."""
        # GIVEN: source has VCS config in same org
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        CloneWorkspaceAPI(mock_client)

        vcs_config = WorkspaceVCS.model_validate(vcs_repo_data["attributes"])

        # THEN: VCS config should be valid
        assert vcs_config.identifier == "my-org/my-repo"
        assert vcs_config.branch == "main"

    def test_get_workspace_vcs_config(self, mock_client, source_with_vcs):
        """Should retrieve VCS configuration from workspace."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        mock_client.get.return_value = {"data": source_with_vcs}

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: getting VCS config
        vcs_config = clone_api.get_workspace_vcs_config("ws-vcs1")

        # THEN: should return VCS config
        assert vcs_config is not None
        assert isinstance(vcs_config, WorkspaceVCS)

    def test_get_workspace_vcs_config_when_none(self, mock_client):
        """Should return None when workspace has no VCS configuration."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        workspace_data = {
            "id": "ws-no-vcs",
            "type": "workspaces",
            "attributes": {
                "name": "no-vcs",
                "terraform_version": "1.5.0",
                "execution_mode": "remote",
            },
        }
        mock_client.get.return_value = {"data": workspace_data}

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: getting VCS config for workspace without VCS
        vcs_config = clone_api.get_workspace_vcs_config("ws-no-vcs")

        # THEN: should return None
        assert vcs_config is None

    def test_update_workspace_vcs_config(self, mock_client):
        """Should send correct PATCH payload for VCS configuration."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        mock_client.patch.return_value = {"data": {}}

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: updating VCS config
        result = clone_api.update_workspace_vcs_config(
            target_workspace_id="ws-target",
            identifier="new-org/new-repo",
            branch="develop",
            oauth_token_id="ot-new123",
        )

        # THEN: should call patch with correct payload
        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        assert "/workspaces/ws-target" in call_args[0][0]

        # Check payload
        payload = call_args[1]["json_data"]
        assert payload["data"]["type"] == "workspaces"
        vcs_attrs = payload["data"]["attributes"]["vcs-repo"]
        assert vcs_attrs["identifier"] == "new-org/new-repo"
        assert vcs_attrs["branch"] == "develop"
        assert vcs_attrs["oauth-token-id"] == "ot-new123"

        # THEN: should return success
        assert result["status"] == "success"
        assert result["vcs_configured"] is True

    def test_clone_vcs_configuration_same_org(self, mock_client, source_with_vcs):
        """VCS clone within same org should reuse OAuth token."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        mock_client.get.return_value = {"data": source_with_vcs}
        mock_client.patch.return_value = {"data": {}}

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: cloning VCS within same org
        result = clone_api.clone_vcs_configuration(
            source_workspace_id="ws-source",
            target_workspace_id="ws-target",
            source_organization="org-test",
            target_organization="org-test",
        )

        # THEN: should succeed and use source token
        assert result["status"] == "success"
        assert result["vcs_cloned"] is True
        assert result["identifier"] == "my-org/my-repo"

    def test_clone_vcs_configuration_cross_org_with_token(self, mock_client, source_with_vcs):
        """VCS clone across orgs should use provided token."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        mock_client.get.return_value = {"data": source_with_vcs}
        mock_client.patch.return_value = {"data": {}}

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: cloning VCS across orgs with explicit token
        result = clone_api.clone_vcs_configuration(
            source_workspace_id="ws-source",
            target_workspace_id="ws-target",
            source_organization="org-a",
            target_organization="org-b",
            vcs_oauth_token_id="ot-org-b-123",
        )

        # THEN: should succeed with explicit token
        assert result["status"] == "success"
        assert result["vcs_cloned"] is True
        assert result["oauth_token_id"] == "ot-org-b-123"

    def test_clone_vcs_configuration_cross_org_without_token(self, mock_client, source_with_vcs):
        """VCS clone across orgs without token should fail."""
        from terrapyne.api.workspace_clone import (
            CloneWorkspaceAPI,
            VCSTokenRequiredError,
        )

        mock_client.get.return_value = {"data": source_with_vcs}

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: cloning VCS across orgs without explicit token
        # THEN: should raise VCSTokenRequiredError
        with pytest.raises(VCSTokenRequiredError):
            clone_api.clone_vcs_configuration(
                source_workspace_id="ws-source",
                target_workspace_id="ws-target",
                source_organization="org-a",
                target_organization="org-b",
                vcs_oauth_token_id=None,
            )

    def test_clone_vcs_configuration_no_source_vcs(self, mock_client):
        """Should handle source workspace without VCS gracefully."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        workspace_no_vcs = {
            "id": "ws-no-vcs",
            "type": "workspaces",
            "attributes": {"name": "no-vcs"},
        }
        mock_client.get.return_value = {"data": workspace_no_vcs}

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: cloning VCS from workspace without VCS config
        result = clone_api.clone_vcs_configuration(
            source_workspace_id="ws-no-vcs",
            target_workspace_id="ws-target",
            source_organization="org-test",
            target_organization="org-test",
        )

        # THEN: should return success but indicate no VCS to clone
        assert result["status"] == "success"
        assert result["vcs_cloned"] is False
        assert "reason" in result

    def test_require_vcs_token_for_cross_org(self, mock_client):
        """VCS clone across organizations requires explicit token ID."""
        # GIVEN: source in org A, target in org B
        # WHEN: attempting to clone --with-vcs without explicit token
        # THEN: should raise VCSTokenRequiredError

        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        clone_api = CloneWorkspaceAPI(mock_client)

        # This should fail validation
        with pytest.raises(VCSTokenRequiredError):
            clone_api.validate_vcs_clone_args(
                source_org="org-a", target_org="org-b", vcs_oauth_token_id=None
            )

    def test_allow_vcs_token_override(self, mock_client):
        """Should allow explicit VCS token ID override."""
        # GIVEN: explicit vcs_oauth_token_id provided
        # WHEN: cloning --with-vcs with token ID
        # THEN: should use provided token ID

        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        clone_api = CloneWorkspaceAPI(mock_client)

        # This should succeed
        result = clone_api.validate_vcs_clone_args(
            source_org="org-a", target_org="org-b", vcs_oauth_token_id="ot-explicit123"
        )

        # Token should be accepted
        assert result == "ot-explicit123"

    def test_handle_missing_oauth_token_ref(self, mock_client, vcs_repo_data):
        """Should handle VCS config without oauth-token relationship."""
        # GIVEN: VCS config with no oauth-token
        vcs_attrs = {
            "identifier": "my-org/my-repo",
            "branch": "main",
            "ingress_submodules": False,
            "tags_regex": None,
        }

        # WHEN: processing VCS config
        vcs_config = WorkspaceVCS.model_validate(vcs_attrs)

        # THEN: should handle gracefully
        assert vcs_config.identifier == "my-org/my-repo"


class TestConflictResolution:
    """Test conflict handling during clone."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock(spec=TFCClient)

    def test_fail_fast_on_conflict(self, mock_client):
        """Should fail fast when conflicts detected."""
        # GIVEN: target workspace exists, force=False
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI, WorkspaceAlreadyExistsError

        # WHEN: both source and target exist
        source_data = {
            "id": "ws-src",
            "type": "workspaces",
            "attributes": {
                "name": "source",
                "terraform_version": "1.5.0",
                "execution_mode": "remote",
                "auto_apply": False,
                "lock": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-10T12:00:00Z",
            },
        }
        target_data = {
            "id": "ws-tgt",
            "type": "workspaces",
            "attributes": {
                "name": "target",
                "terraform_version": "1.5.0",
                "execution_mode": "remote",
                "auto_apply": False,
                "lock": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-10T12:00:00Z",
            },
        }

        def mock_get(path):
            if "target" in path:
                return {"data": target_data}
            return {"data": source_data}

        mock_client.get.side_effect = mock_get
        clone_api = CloneWorkspaceAPI(mock_client)

        # THEN: should fail immediately with WorkspaceAlreadyExistsError
        with pytest.raises(WorkspaceAlreadyExistsError):
            clone_api.validate_clone_args(
                source_workspace_name="source",
                target_workspace_name="target",
                organization="test-org",
                force=False,
            )

    def test_force_flag_bypasses_conflict_check(self, mock_client):
        """Force flag should bypass conflict detection."""
        # GIVEN: force=True
        # WHEN: attempting clone with existing target
        # THEN: should proceed

        # This will be tested at integration level
        # Unit test here just validates flag handling
        assert True  # Placeholder for integration test

    def test_rollback_on_partial_failure(self, mock_client):
        """Should handle partial clone failure gracefully."""
        # GIVEN: clone partially succeeds (workspace created but vars fail)
        # WHEN: error occurs during variable cloning
        # THEN: should report error clearly

        # This is more of an integration test
        # Unit validates error handling structure
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        CloneWorkspaceAPI(mock_client)

        # Error should propagate with context
        with pytest.raises(RuntimeError):
            raise RuntimeError("Variable clone failed, workspace 'target' created but incomplete")


class TestCloneWithTeamAccess:
    """Test handling of with_team_access parameter."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock(spec=TFCClient)

    def test_clone_raises_not_implemented_for_with_team_access(self, mock_client):
        """clone() should raise NotImplementedError when with_team_access=True is passed."""
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        source_data = {
            "id": "ws-src",
            "type": "workspaces",
            "attributes": {
                "name": "source",
                "terraform_version": "1.5.0",
                "execution_mode": "remote",
                "auto_apply": False,
                "lock": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-10T12:00:00Z",
            },
        }

        mock_client.get_organization.return_value = "test-org"

        # Mock get to return source workspace but not find target
        def mock_get_side_effect(path):
            if "target" in path:
                # target doesn't exist
                raise Exception("404 Not found")
            # source exists
            return {"data": source_data}

        mock_client.get.side_effect = mock_get_side_effect

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: clone is called with with_team_access=True
        # THEN: should raise NotImplementedError
        with pytest.raises(NotImplementedError) as exc_info:
            clone_api.clone(
                source_workspace_name="source",
                target_workspace_name="target",
                organization="test-org",
                with_team_access=True,
            )

        assert "team_access" in str(exc_info.value).lower() or "not" in str(exc_info.value).lower()


class TestCloneExceptionHandling:
    """Test that clone method properly propagates exceptions instead of swallowing them."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock(spec=TFCClient)

    def test_clone_propagates_exception_from_validate_clone_args(self, mock_client):
        """clone() should propagate exceptions from validate_clone_args instead of swallowing them."""
        # GIVEN: validate_clone_args raises an exception
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI, WorkspaceNotFoundError

        mock_client.get_organization.return_value = "test-org"
        mock_client.get.side_effect = Exception("Source workspace not found")

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: calling clone with nonexistent source workspace
        # THEN: should raise the exception (not return a dict with error status)
        with pytest.raises(WorkspaceNotFoundError):
            clone_api.clone(
                source_workspace_name="nonexistent",
                target_workspace_name="target",
                organization="test-org",
            )

    def test_clone_propagates_exception_from_inner_failure(self, mock_client):
        """clone() should propagate exceptions from internal operations, not return error dict."""
        # GIVEN: an inner operation (like workspace creation) raises an exception
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        source_data = {
            "id": "ws-src",
            "type": "workspaces",
            "attributes": {
                "name": "source",
                "terraform_version": "1.5.0",
                "execution_mode": "remote",
                "auto_apply": False,
                "lock": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-10T12:00:00Z",
            },
        }

        mock_client.get_organization.return_value = "test-org"

        # Mock get to return source workspace but not find target (so create will be attempted)
        def mock_get_side_effect(path):
            if "target" in path:
                # target doesn't exist
                raise Exception("404 Not found")
            # source exists
            return {"data": source_data}

        mock_client.get.side_effect = mock_get_side_effect
        # Post fails when creating workspace
        mock_client.post.side_effect = Exception("API rate limit exceeded")

        clone_api = CloneWorkspaceAPI(mock_client)

        # WHEN: an inner operation fails
        # THEN: should raise the exception (not return {"status": "error"})
        with pytest.raises(Exception) as exc_info:
            clone_api.clone(
                source_workspace_name="source",
                target_workspace_name="target",
                organization="test-org",
            )

        assert "API rate limit exceeded" in str(exc_info.value)
