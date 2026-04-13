"""Unit tests for context detection utilities."""

import json
import os
from unittest.mock import MagicMock, patch

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

    def test_valid_tfstate_with_workspace_name(self, tmp_path):
        """Test reading valid tfstate with workspace name."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_data = {
            "backend": {
                "config": {
                    "organization": "Takeda",
                    "hostname": "app.terraform.io",
                    "workspaces": {"name": "my-workspace"},
                }
            }
        }

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text(json.dumps(tfstate_data))

        workspace, org, hostname = get_context_from_tfstate(tmp_path)

        assert workspace == "my-workspace"
        assert org == "Takeda"
        assert hostname == "app.terraform.io"

    def test_valid_tfstate_without_workspace(self, tmp_path):
        """Test reading tfstate without workspace name."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_data = {
            "backend": {
                "config": {
                    "organization": "MyOrg",
                    "hostname": "tfe.example.com",
                }
            }
        }

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text(json.dumps(tfstate_data))

        workspace, org, hostname = get_context_from_tfstate(tmp_path)

        assert workspace is None
        assert org == "MyOrg"
        assert hostname == "tfe.example.com"

    def test_tfstate_defaults_hostname(self, tmp_path):
        """Test that hostname defaults to app.terraform.io."""
        terraform_dir = tmp_path / ".terraform"
        terraform_dir.mkdir()

        tfstate_data = {
            "backend": {
                "config": {
                    "organization": "Takeda",
                    "workspaces": {"name": "test"},
                }
            }
        }

        tfstate_file = terraform_dir / "terraform.tfstate"
        tfstate_file.write_text(json.dumps(tfstate_data))

        _, _, hostname = get_context_from_tfstate(tmp_path)
        assert hostname == "app.terraform.io"

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

    def test_explicit_workspace_arg(self):
        """Test that explicit workspace argument is returned."""
        result = resolve_workspace("explicit-workspace")
        assert result == "explicit-workspace"

    def test_fallback_to_context(self):
        """Test fallback to detected context."""
        with patch(
            "terrapyne.utils.context.get_workspace_context",
            return_value=("detected-workspace", "Org", "app.terraform.io"),
        ):
            result = resolve_workspace(None)

        assert result == "detected-workspace"

    def test_no_workspace_detected(self):
        """Test when no workspace can be resolved."""
        with patch(
            "terrapyne.utils.context.get_workspace_context", return_value=(None, None, None)
        ):
            result = resolve_workspace(None)

        assert result is None


class TestResolveOrganization:
    """Test resolve_organization function."""

    def test_explicit_org_arg(self):
        """Test that explicit organization argument is returned."""
        result = resolve_organization("explicit-org")
        assert result == "explicit-org"

    def test_fallback_to_env_var(self):
        """Test fallback to TFC_ORG environment variable."""
        with patch.dict(os.environ, {"TFC_ORG": "env-org"}):
            result = resolve_organization(None)

        assert result == "env-org"

    def test_fallback_to_context(self):
        """Test fallback to detected context when no env var."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "terrapyne.utils.context.get_workspace_context",
                return_value=("workspace", "context-org", "app.terraform.io"),
            ):
                result = resolve_organization(None)

        assert result == "context-org"

    def test_no_organization_detected(self):
        """Test when no organization can be resolved."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "terrapyne.utils.context.get_workspace_context",
                return_value=(None, None, None),
            ):
                result = resolve_organization(None)

        assert result is None

    def test_env_var_takes_precedence_over_context(self):
        """Test that TFC_ORG env var takes precedence over detected context."""
        with patch.dict(os.environ, {"TFC_ORG": "env-org"}):
            with patch(
                "terrapyne.utils.context.get_workspace_context",
                return_value=("workspace", "context-org", "app.terraform.io"),
            ):
                result = resolve_organization(None)

        assert result == "env-org"
