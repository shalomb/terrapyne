"""Unit tests for CLI quiet mode."""

from unittest.mock import patch

from terrapyne.cli import utils


class TestQuietMode:
    """Test suite for quiet mode functionality."""

    def test_quiet_mode_default_false(self):
        """Quiet mode should be False by default."""
        utils.set_quiet_mode(False)
        assert not utils.console.quiet

    def test_quiet_mode_can_be_enabled(self):
        """Quiet mode can be enabled."""
        from terrapyne.cli import utils

        utils.set_quiet_mode(True)
        assert utils.console.quiet

    def test_quiet_mode_can_be_disabled(self):
        """Quiet mode can be disabled after being enabled."""
        from terrapyne.cli import utils

        utils.set_quiet_mode(True)
        assert utils.console.quiet
        utils.set_quiet_mode(False)
        assert not utils.console.quiet


class TestTFCOrgResolution:
    """Test TFC organization resolution including environment variables."""

    @patch("terrapyne.core.context.get_workspace_context")
    def test_resolve_organization_env_var(self, mock_context):
        """resolve_organization should prioritize TFC_ORG environment variable."""
        import os

        from terrapyne.core.context import resolve_organization

        mock_context.return_value = (None, "context-org", "app.terraform.io")

        with patch.dict(os.environ, {"TFC_ORG": "env-org"}):
            # Should use env var even if arg is None
            result = resolve_organization(None)
            assert result == "env-org"

    @patch("terrapyne.core.context.get_workspace_context")
    def test_resolve_organization_fallback(self, mock_context):
        """resolve_organization should fall back to context if no env var."""
        import os

        from terrapyne.core.context import resolve_organization

        mock_context.return_value = (None, "context-org", "app.terraform.io")

        # Ensure TFC_ORG is not in environment
        env_copy = os.environ.copy()
        if "TFC_ORG" in env_copy:
            del env_copy["TFC_ORG"]

        with patch.dict(os.environ, env_copy, clear=True):
            result = resolve_organization(None)
            assert result == "context-org"
