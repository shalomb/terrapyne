"""Tests for VCS model properties and credentials edge cases."""

from terrapyne.models.vcs import VCSConnection


class TestVCSConnectionProperties:
    def _make_vcs(self, **overrides):
        defaults = {
            "identifier": "org/repo",
            "oauth-token-id": "ot-abc123xyz",
            "service-provider": "github",
            "repository-http-url": "https://github.com/org/repo",
        }
        defaults.update(overrides)
        return VCSConnection.from_api_response(defaults)

    def test_github_url(self):
        vcs = self._make_vcs()
        assert vcs.github_url == "https://github.com/org/repo"

    def test_github_url_non_github(self):
        vcs = self._make_vcs(**{"service-provider": "gitlab"})
        assert vcs.github_url is None

    def test_owner(self):
        assert self._make_vcs().owner == "org"

    def test_owner_no_slash(self):
        vcs = self._make_vcs(identifier="flat-name")
        assert vcs.owner is None

    def test_repo_name(self):
        assert self._make_vcs().repo_name == "repo"

    def test_repo_name_no_slash(self):
        vcs = self._make_vcs(identifier="flat-name")
        assert vcs.repo_name is None

    def test_masked_oauth_token(self):
        vcs = self._make_vcs()
        assert vcs.masked_oauth_token == "ot-***"

    def test_masked_oauth_token_short(self):
        vcs = self._make_vcs(**{"oauth-token-id": "ab"})
        assert vcs.masked_oauth_token == "***"
