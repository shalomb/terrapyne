"""Tests for RunsAPI.list pagination honesty (EPIC-005).

Verifies that RunsAPI.list paginates beyond 100 when limit > 100,
fetches all when limit is None, and respects the requested limit.
"""

from unittest.mock import MagicMock

import pytest

from terrapyne.api.runs import RunsAPI


def _make_run_item(run_id: str) -> dict:
    """Create a minimal run API response item."""
    return {
        "id": run_id,
        "type": "runs",
        "attributes": {
            "status": "applied",
            "created-at": "2024-01-15T10:00:00Z",
            "message": None,
            "auto-apply": False,
            "is-destroy": False,
        },
    }


def _make_page_response(run_ids: list[str], total_count: int, has_next: bool) -> dict:
    """Create a paginated API response."""
    return {
        "data": [_make_run_item(rid) for rid in run_ids],
        "included": [],
        "meta": {"pagination": {"total-count": total_count}},
        "links": {"next": "/next-page" if has_next else None},
    }


class TestRunsListPaginationHonesty:
    """RunsAPI.list must paginate beyond a single page when limit > 100."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        return RunsAPI(mock_client)

    def test_limit_greater_than_100_paginates(self, api, mock_client):
        """Given 250 runs, limit=200 should fetch 2 pages and return 200 runs."""
        page1_ids = [f"run-{i:03d}" for i in range(100)]
        page2_ids = [f"run-{i:03d}" for i in range(100, 200)]

        mock_client.get.side_effect = [
            _make_page_response(page1_ids, total_count=250, has_next=True),
            _make_page_response(page2_ids, total_count=250, has_next=True),
        ]

        runs, total_count = api.list("ws-test", limit=200)

        assert len(runs) == 200
        assert total_count == 250
        assert mock_client.get.call_count == 2

    def test_limit_none_fetches_all(self, api, mock_client):
        """Given 250 runs, limit=None should fetch all 3 pages."""
        page1_ids = [f"run-{i:03d}" for i in range(100)]
        page2_ids = [f"run-{i:03d}" for i in range(100, 200)]
        page3_ids = [f"run-{i:03d}" for i in range(200, 250)]

        mock_client.get.side_effect = [
            _make_page_response(page1_ids, total_count=250, has_next=True),
            _make_page_response(page2_ids, total_count=250, has_next=True),
            _make_page_response(page3_ids, total_count=250, has_next=False),
        ]

        runs, total_count = api.list("ws-test", limit=None)

        assert len(runs) == 250
        assert total_count == 250
        assert mock_client.get.call_count == 3

    def test_limit_within_single_page_no_extra_requests(self, api, mock_client):
        """limit=20 with 50 available should make one request and return 20."""
        all_ids = [f"run-{i:03d}" for i in range(50)]

        mock_client.get.return_value = _make_page_response(all_ids, total_count=50, has_next=False)

        runs, total_count = api.list("ws-test", limit=20)

        assert len(runs) == 20
        assert total_count == 50
        assert mock_client.get.call_count == 1

    def test_pagination_passes_page_number(self, api, mock_client):
        """Verify page[number] increments on each request."""
        page1_ids = [f"run-{i:03d}" for i in range(100)]
        page2_ids = [f"run-{i:03d}" for i in range(100, 150)]

        mock_client.get.side_effect = [
            _make_page_response(page1_ids, total_count=150, has_next=True),
            _make_page_response(page2_ids, total_count=150, has_next=False),
        ]

        _runs, _total_count = api.list("ws-test", limit=150)

        # Check page numbers in calls
        first_call_params = mock_client.get.call_args_list[0][1]["params"]
        second_call_params = mock_client.get.call_args_list[1][1]["params"]
        assert first_call_params["page[number]"] == 1
        assert second_call_params["page[number]"] == 2

    def test_status_filter_preserved_across_pages(self, api, mock_client):
        """Status filter must be sent on every page request."""
        page1_ids = [f"run-{i:03d}" for i in range(100)]
        page2_ids = [f"run-{i:03d}" for i in range(100, 120)]

        mock_client.get.side_effect = [
            _make_page_response(page1_ids, total_count=120, has_next=True),
            _make_page_response(page2_ids, total_count=120, has_next=False),
        ]

        _runs, _total_count = api.list("ws-test", limit=120, status="errored")

        for c in mock_client.get.call_args_list:
            assert c[1]["params"]["filter[status]"] == "errored"
