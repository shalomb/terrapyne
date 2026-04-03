"""Test project find uses server-side filtering."""

from unittest.mock import MagicMock

from terrapyne.api.projects import ProjectAPI


class TestProjectListFiltering:
    def _make_client(self):
        mock = MagicMock()
        mock.get_organization.return_value = "test-org"
        mock.paginate_with_meta.return_value = (iter([]), None)
        return mock

    def _get_params(self, client):
        return client.paginate_with_meta.call_args.kwargs.get("params", {})

    def test_exact_name_uses_filter_names(self):
        """No wildcards → use filter[names] for exact server-side match."""
        client = self._make_client()
        api = ProjectAPI(client)
        list(api.list("test-org", search="93126-MAN")[0])

        params = self._get_params(client)
        assert "filter[names]" in params
        assert params["filter[names]"] == "93126-MAN"

    def test_wildcard_uses_q_param(self):
        """Wildcards → use q= for substring search."""
        client = self._make_client()
        api = ProjectAPI(client)
        list(api.list("test-org", search="*-MAN")[0])

        params = self._get_params(client)
        assert "q" in params
        assert "filter[names]" not in params

    def test_no_search_sends_no_filter(self):
        """No search → no filter params."""
        client = self._make_client()
        api = ProjectAPI(client)
        list(api.list("test-org")[0])

        params = self._get_params(client)
        assert "q" not in params
        assert "filter[names]" not in params
