"""Tests for TFCClient."""

from unittest.mock import patch

from terrapyne.api.client import TFCClient


class TestTFCClientCachedProperty:
    """Test cached_property behavior on TFCClient API accessors."""

    def test_workspaces_cached_same_instance(self):
        """Verify that workspaces accessor returns the same instance on multiple accesses."""
        with patch("terrapyne.core.credentials.TerraformCredentials.load"):
            client = TFCClient(organization="test-org")

            # Access workspaces property twice
            ws1 = client.workspaces
            ws2 = client.workspaces

            # Should be the same instance (cached)
            assert ws1 is ws2

    def test_runs_cached_same_instance(self):
        """Verify that runs accessor returns the same instance on multiple accesses."""
        with patch("terrapyne.core.credentials.TerraformCredentials.load"):
            client = TFCClient(organization="test-org")

            # Access runs property twice
            runs1 = client.runs
            runs2 = client.runs

            # Should be the same instance (cached)
            assert runs1 is runs2

    def test_projects_cached_same_instance(self):
        """Verify that projects accessor returns the same instance on multiple accesses."""
        with patch("terrapyne.core.credentials.TerraformCredentials.load"):
            client = TFCClient(organization="test-org")

            # Access projects property twice
            proj1 = client.projects
            proj2 = client.projects

            # Should be the same instance (cached)
            assert proj1 is proj2

    def test_teams_cached_same_instance(self):
        """Verify that teams accessor returns the same instance on multiple accesses."""
        with patch("terrapyne.core.credentials.TerraformCredentials.load"):
            client = TFCClient(organization="test-org")

            # Access teams property twice
            teams1 = client.teams
            teams2 = client.teams

            # Should be the same instance (cached)
            assert teams1 is teams2

    def test_state_versions_cached_same_instance(self):
        """Verify that state_versions accessor returns the same instance on multiple accesses."""
        with patch("terrapyne.core.credentials.TerraformCredentials.load"):
            client = TFCClient(organization="test-org")

            # Access state_versions property twice
            sv1 = client.state_versions
            sv2 = client.state_versions

            # Should be the same instance (cached)
            assert sv1 is sv2
