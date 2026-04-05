"""Tests for VCS models oauth_token_id reconciliation."""

import pytest
from terrapyne.models.vcs import VCSConnection
from terrapyne.models.workspace import WorkspaceVCS


class TestVCSConnectionOAuthTokenId:
    """Test VCSConnection oauth_token_id field."""

    def test_vcsconnection_allows_optional_oauth_token_id(self):
        """VCSConnection should allow oauth_token_id to be optional."""
        # GIVEN: VCSConnection data without oauth_token_id
        data = {
            "identifier": "owner/repo",
            "service-provider": "github",
        }

        # WHEN: creating VCSConnection without oauth_token_id
        vc = VCSConnection.model_validate(data)

        # THEN: should create successfully with None oauth_token_id
        assert vc.oauth_token_id is None
        assert vc.identifier == "owner/repo"

    def test_vcsconnection_with_oauth_token_id(self):
        """VCSConnection should accept oauth_token_id."""
        # GIVEN: valid VCSConnection data with oauth_token_id
        data = {
            "identifier": "owner/repo",
            "oauth-token-id": "ot-12345",
            "service-provider": "github",
        }

        # WHEN: creating VCSConnection
        vc = VCSConnection.model_validate(data)

        # THEN: should create successfully
        assert vc.oauth_token_id == "ot-12345"


class TestWorkspaceVCSOAuthTokenId:
    """Test WorkspaceVCS oauth_token_id field."""

    def test_workspacevcs_allows_missing_oauth_token_id(self):
        """WorkspaceVCS should allow oauth_token_id to be optional."""
        # GIVEN: WorkspaceVCS data without oauth_token_id
        data = {
            "identifier": "owner/repo",
        }

        # WHEN: creating WorkspaceVCS
        wvcs = WorkspaceVCS.model_validate(data)

        # THEN: should create successfully with None oauth_token_id
        assert wvcs.oauth_token_id is None

    def test_workspacevcs_with_oauth_token_id(self):
        """WorkspaceVCS should accept oauth_token_id when provided."""
        # GIVEN: valid WorkspaceVCS data with oauth_token_id
        data = {
            "identifier": "owner/repo",
            "oauth-token-id": "ot-12345",
        }

        # WHEN: creating WorkspaceVCS
        wvcs = WorkspaceVCS.model_validate(data)

        # THEN: should create successfully
        assert wvcs.oauth_token_id == "ot-12345"


class TestOAuthTokenIdConsistency:
    """Test consistency between VCSConnection and WorkspaceVCS."""

    def test_oauth_token_id_is_optional_in_both(self):
        """Both models should have consistent oauth_token_id optionality.

        WorkspaceVCS represents a workspace's VCS connection, which may not
        always have OAuth token ID set (e.g., incomplete setup, manual setup).
        VCSConnection should also allow optional oauth_token_id for consistency.
        """
        # WorkspaceVCS allows None
        wvcs = WorkspaceVCS.model_validate({"identifier": "owner/repo"})
        assert wvcs.oauth_token_id is None

        # VCSConnection should also allow None for consistency
        vc = VCSConnection.model_validate({"identifier": "owner/repo"})
        assert vc.oauth_token_id is None
