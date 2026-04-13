"""Unit tests for context detection utilities."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from terrapyne.utils.context import (
    get_context_from_tfstate,
    get_workspace_context,
    resolve_organization,
    resolve_workspace,
)


class TestGetContextFromTFState:
    """Test get_context_from_tfstate function."""

    def test_no_tfstate_file(self, tmp_path):
        """Test when .terraform/terraform.tfstate doesn't exist."""
        result = get_context_from_tfstate(tmp_path)
        assert result == (None, None, None)

    @pytest.mark.parametrize(
        "backend_config,expected_workspace,expected_org,expected_hostname",
        [
            # With all fields
            (
                {
                    "organization": "Takeda",
                    "hostname": "app.terraform.io",
                    "workspaces": {"name": "my-workspace"},
                },
                "my-workspace",
                "Takeda",
                "app.terraform.io",
            ),
            # Without workspace name
            (
                {
                    "organization": "MyOrg",
                    "hostname": "tfe.example.com",
                },
                None,
                "MyOrg",
                "tfe.example.com",
            ),
            # Missing hostname (should default)
            (
                {
                    "organization": "Takeda",
                    "workspaces": {"name": "test"},
                },
                "test",
                "Takeda",
                "app.terraform.io",
            ),
            # Workspace with prefix (not name)
            (
                {
                    "organization": "Takeda",
                    "workspaces": {"prefix": "env-"},
                },
                None,
                "Takeda",
                "app.terraform.io",
            ),
        ],
        ids=[
            "valid_tfstate_with_all_fields",
            "valid_tfstate_without_workspace",
            "hostname_defaults_to_app_terraform_io",
            "workspaces_as_prefix_not_name",
        ],
    )
    def test_valid_tfstate_variants(
        self, tmp_path, backend_config, expected_workspace, expected_org, expected_hostname
    ):
        """Test reading tfstate with various backend configurations."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_data = {"backend": {"config": backend_config}}

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text(json.dumps(tfstate_data))

        workspace, org, hostname = get_context_from_tfstate(tmp_path)

        assert workspace == expected_workspace
        assert org == expected_org
        assert hostname == expected_hostname

    def test_tfstate_invalid_json(self, tmp_path):
        """Test handling of invalid JSON in tfstate."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text("{invalid json")

        result = get_context_from_tfstate(tmp_path)
        assert result == (None, None, None)

    def test_tfstate_missing_backend(self, tmp_path):
        """Test tfstate without backend section."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_data = {"other": "data"}

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text(json.dumps(tfstate_data))

        # When backend config is empty, hostname defaults to app.terraform.io
        result = get_context_from_tfstate(tmp_path)
        assert result == (None, None, "app.terraform.io")

    def test_tfstate_workspaces_as_list(self, tmp_path):
        """Test tfstate with workspaces as non-dict (e.g., prefix mode)."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_data = {
            "backend": {
                "config": {
                    "organization": "Takeda",
                    "workspaces": {"prefix": "env-"},  # Not a "name" entry
                }
            }
        }

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text(json.dumps(tfstate_data))

        workspace, org, _ = get_context_from_tfstate(tmp_path)

        assert workspace is None
        assert org == "Takeda"

    def test_tfstate_permission_error(self, tmp_path):
        """Test handling of permission error when reading tfstate."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text(json.dumps({"backend": {"config": {}}}))

        # Make file unreadable
        tfstate_file.chmod(0o000)

        try:
            result = get_context_from_tfstate(tmp_path)
            assert result == (None, None, None)
        finally:
            # Restore permissions for cleanup
            tfstate_file.chmod(0o644)

    def test_default_directory_uses_cwd(self, tmp_path):
        """Test that directory defaults to current working directory."""
        with patch("terrapyne.utils.context.Path.cwd", return_value=tmp_path):
            result = get_context_from_tfstate(None)

        # Should return None values since no tfstate exists in tmp_path
        assert result == (None, None, None)


class TestGetWorkspaceContext:
    """Test get_workspace_context function."""

    def test_context_from_tfstate(self, tmp_path):
        """Test that tfstate takes priority over terraform.tf."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_data = {
            "backend": {
                "config": {
                    "organization": "TFStateOrg",
                    "workspaces": {"name": "tfstate-workspace"},
                }
            }
        }

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text(json.dumps(tfstate_data))

        with patch("terrapyne.utils.context.Path.cwd", return_value=tmp_path):
            workspace, org, _ = get_workspace_context()

        assert workspace == "tfstate-workspace"
        assert org == "TFStateOrg"

    def test_context_from_backend_when_tfstate_fails(self, tmp_path):
        """Test fallback to terraform.tf parsing."""
        mock_backend = MagicMock()
        mock_backend.workspace_name = "backend-workspace"
        mock_backend.organization = "BackendOrg"
        mock_backend.hostname = "tfe.example.com"

        with patch(
            "terrapyne.utils.context.get_context_from_tfstate", return_value=(None, None, None)
        ):
            with patch("terrapyne.utils.context.detect_backend", return_value=mock_backend):
                workspace, org, hostname = get_workspace_context()

        assert workspace == "backend-workspace"
        assert org == "BackendOrg"
        assert hostname == "tfe.example.com"

    def test_no_backend_detected(self):
        """Test when no backend is detected."""
        with patch(
            "terrapyne.utils.context.get_context_from_tfstate", return_value=(None, None, None)
        ):
            with patch("terrapyne.utils.context.detect_backend", return_value=None):
                result = get_workspace_context()

        assert result == (None, None, None)

    def test_backend_with_no_workspace_name(self):
        """Test backend with None workspace_name."""
        mock_backend = MagicMock()
        mock_backend.workspace_name = None
        mock_backend.organization = "Org"
        mock_backend.hostname = "app.terraform.io"

        with patch(
            "terrapyne.utils.context.get_context_from_tfstate", return_value=(None, None, None)
        ):
            with patch("terrapyne.utils.context.detect_backend", return_value=mock_backend):
                workspace, org, _ = get_workspace_context()

        assert workspace is None
        assert org == "Org"


class TestResolveWorkspace:
    """Test resolve_workspace function."""

    @pytest.mark.parametrize(
        "arg,context,expected",
        [
            # Explicit argument always wins
            ("explicit-workspace", (None, None, None), "explicit-workspace"),
            ("my-workspace", ("detected", "org", "host"), "my-workspace"),
            # Fallback to detected context
            (None, ("detected-workspace", "Org", "app.terraform.io"), "detected-workspace"),
            # No workspace detected
            (None, (None, None, None), None),
        ],
        ids=[
            "explicit_arg_takes_precedence",
            "explicit_arg_overrides_context",
            "fallback_to_context",
            "no_workspace_detected",
        ],
    )
    def test_resolve_workspace(self, arg, context, expected):
        """Test resolve_workspace with various argument and context combinations."""
        with patch(
            "terrapyne.utils.context.get_workspace_context",
            return_value=context,
        ):
            result = resolve_workspace(arg)

        assert result == expected


class TestResolveOrganization:
    """Test resolve_organization function."""

    @pytest.mark.parametrize(
        "arg,env_var,context,expected",
        [
            # Explicit argument always wins
            ("explicit-org", None, (None, None, None), "explicit-org"),
            ("my-org", "env-org", ("ws", "ctx-org", "host"), "my-org"),
            # Fallback to environment variable
            (None, "env-org", (None, None, None), "env-org"),
            # Fallback to context when no env var
            (None, None, ("workspace", "context-org", "app.terraform.io"), "context-org"),
            # Env var takes precedence over context
            (None, "env-org", ("workspace", "context-org", "app.terraform.io"), "env-org"),
            # No organization detected
            (None, None, (None, None, None), None),
        ],
        ids=[
            "explicit_arg_takes_precedence",
            "explicit_arg_over_env_and_context",
            "fallback_to_env_var",
            "fallback_to_context",
            "env_var_over_context",
            "no_organization_detected",
        ],
    )
    def test_resolve_organization(self, arg, env_var, context, expected):
        """Test resolve_organization with various argument, env, and context combinations."""
        env_dict = {"TFC_ORG": env_var} if env_var else {}
        with patch.dict(os.environ, env_dict, clear=True):
            with patch(
                "terrapyne.utils.context.get_workspace_context",
                return_value=context,
            ):
                result = resolve_organization(arg)

        assert result == expected
