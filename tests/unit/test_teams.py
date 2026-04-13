"""Tests for TeamsAPI — server-side filtering and project access operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from terrapyne.api.teams import TeamsAPI
from terrapyne.models.team_access import (
    TeamProjectAccess,
    TeamProjectAccessComparison,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_team_response(team_id: str, name: str, members: int = 0) -> dict:
    return {
        "id": team_id,
        "type": "teams",
        "attributes": {
            "name": name,
            "users-count": members,
            "visibility": "secret",
            "organization-access": {},
        },
        "relationships": {"organization": {"data": {"id": "my-org", "type": "organizations"}}},
    }


def _make_team_project_access_response(
    record_id: str,
    team_id: str,
    project_id: str,
    access: str = "admin",
    runs: str = "apply",
) -> dict:
    return {
        "id": record_id,
        "type": "team-projects",
        "attributes": {
            "access": access,
            "project-access": {
                "settings": "delete",
                "teams": "manage",
                "variable-sets": "write",
            },
            "workspace-access": {
                "runs": runs,
                "variables": "write",
                "state-versions": "write",
                "sentinel-mocks": "read",
                "create": True,
                "locking": True,
                "delete": True,
                "move": True,
                "run-tasks": True,
            },
        },
        "relationships": {
            "team": {"data": {"id": team_id, "type": "teams"}},
            "project": {"data": {"id": project_id, "type": "projects"}},
        },
    }


def _make_client_mock() -> MagicMock:
    client = MagicMock()
    client.get_organization.return_value = "my-org"
    return client


# ---------------------------------------------------------------------------
# list_teams — server-side filtering
# ---------------------------------------------------------------------------


class TestListTeamsServerSideFiltering:
    """list_teams() must pass filter params to the API rather than filter client-side."""

    @pytest.mark.parametrize(
        "search,names,expected_params",
        [
            # No filters
            (None, None, {}),
            # Search only (forwarded as q parameter)
            ("platform", None, {"q": "platform"}),
            # Names only (forwarded as filter[names])
            (
                None,
                ["platform-developer", "platform-viewer"],
                {"filter[names]": "platform-developer,platform-viewer"},
            ),
            # Both filters combined
            ("platform", ["platform-admin"], {"q": "platform", "filter[names]": "platform-admin"}),
        ],
        ids=[
            "no_filters",
            "search_only",
            "names_only",
            "search_and_names_combined",
        ],
    )
    def test_list_teams_filters(self, search, names, expected_params):
        """Test list_teams parameter handling for various filter combinations."""
        client = _make_client_mock()
        client.paginate_with_meta.return_value = (iter([]), 0)

        api = TeamsAPI(client)
        api.list_teams(organization="my-org", search=search, names=names)

        client.paginate_with_meta.assert_called_once_with(
            "/organizations/my-org/teams", params=expected_params
        )

    def test_returns_team_instances(self):
        client = _make_client_mock()
        raw = [
            _make_team_response("team-aaa", "platform-developer", members=3),
            _make_team_response("team-bbb", "platform-viewer", members=1),
        ]
        client.paginate_with_meta.return_value = (iter(raw), 2)

        api = TeamsAPI(client)
        teams_iter, total = api.list_teams(organization="my-org", search="platform")
        teams = list(teams_iter)

        assert total == 2
        assert len(teams) == 2
        assert teams[0].id == "team-aaa"
        assert teams[0].name == "platform-developer"
        assert teams[1].id == "team-bbb"


# ---------------------------------------------------------------------------
# get_project_access
# ---------------------------------------------------------------------------


class TestGetProjectAccess:
    def test_returns_matching_record(self):
        client = _make_client_mock()
        raw = [
            _make_team_project_access_response("tprj-111", "team-aaa", "prj-001"),
            _make_team_project_access_response("tprj-222", "team-bbb", "prj-001"),
        ]
        client.paginate.return_value = iter(raw)

        api = TeamsAPI(client)
        result = api.get_project_access(project_id="prj-001", team_id="team-aaa")

        assert result.id == "tprj-111"
        assert result.team_id == "team-aaa"
        assert result.access == "admin"

        client.paginate.assert_called_once_with(
            "/team-projects",
            params={"filter[project][id]": "prj-001"},
        )

    def test_raises_when_team_not_in_project(self):
        client = _make_client_mock()
        raw = [_make_team_project_access_response("tprj-111", "team-aaa", "prj-001")]
        client.paginate.return_value = iter(raw)

        api = TeamsAPI(client)
        with pytest.raises(ValueError, match="No project access record found"):
            api.get_project_access(project_id="prj-001", team_id="team-zzz")


# ---------------------------------------------------------------------------
# set_project_access
# ---------------------------------------------------------------------------


class TestSetProjectAccess:
    def test_patches_existing_record(self):
        client = _make_client_mock()
        existing_raw = [
            _make_team_project_access_response("tprj-111", "team-aaa", "prj-001", access="read")
        ]
        client.paginate.return_value = iter(existing_raw)

        updated_raw = _make_team_project_access_response(
            "tprj-111", "team-aaa", "prj-001", access="admin"
        )
        client.patch.return_value = {"data": updated_raw}

        api = TeamsAPI(client)
        result = api.set_project_access(project_id="prj-001", team_id="team-aaa", access="admin")

        client.patch.assert_called_once_with(
            "/team-projects/tprj-111",
            json_data={"data": {"type": "team-projects", "attributes": {"access": "admin"}}},
        )
        assert result.access == "admin"

    @pytest.mark.parametrize("access", ["admin", "maintain", "write", "read"])
    def test_accepts_all_valid_access_levels(self, access: str):
        client = _make_client_mock()
        existing_raw = [_make_team_project_access_response("tprj-111", "team-aaa", "prj-001")]
        client.paginate.return_value = iter(existing_raw)
        client.patch.return_value = {
            "data": _make_team_project_access_response(
                "tprj-111", "team-aaa", "prj-001", access=access
            )
        }

        api = TeamsAPI(client)
        result = api.set_project_access(project_id="prj-001", team_id="team-aaa", access=access)
        assert result.access == access

    def test_rejects_invalid_access_level(self):
        client = _make_client_mock()
        api = TeamsAPI(client)

        with pytest.raises(ValueError, match="Invalid access level"):
            api.set_project_access(project_id="prj-001", team_id="team-aaa", access="superadmin")


# ---------------------------------------------------------------------------
# compare_project_access
# ---------------------------------------------------------------------------


class TestCompareProjectAccess:
    def _make_access(
        self, record_id: str, team_id: str, project_id: str, runs: str = "apply"
    ) -> TeamProjectAccess:
        return TeamProjectAccess.from_api_response(
            _make_team_project_access_response(record_id, team_id, project_id, runs=runs)
        )

    def test_identical_records_returns_no_diffs(self):
        client = _make_client_mock()
        raw_a = [_make_team_project_access_response("tprj-111", "team-aaa", "prj-001")]
        raw_b = [_make_team_project_access_response("tprj-222", "team-bbb", "prj-002")]
        client.paginate.side_effect = [iter(raw_a), iter(raw_b)]

        api = TeamsAPI(client)
        comparison = api.compare_project_access(
            project_id_a="prj-001",
            team_id_a="team-aaa",
            project_id_b="prj-002",
            team_id_b="team-bbb",
        )

        assert comparison.identical is True
        assert comparison.diffs == []

    def test_different_runs_permission_shows_diff(self):
        client = _make_client_mock()
        raw_a = [
            _make_team_project_access_response("tprj-111", "team-aaa", "prj-001", runs="apply")
        ]
        raw_b = [_make_team_project_access_response("tprj-222", "team-bbb", "prj-002", runs="read")]
        client.paginate.side_effect = [iter(raw_a), iter(raw_b)]

        api = TeamsAPI(client)
        comparison = api.compare_project_access(
            project_id_a="prj-001",
            team_id_a="team-aaa",
            project_id_b="prj-002",
            team_id_b="team-bbb",
        )

        assert comparison.identical is False
        diff_fields = [d.field for d in comparison.diffs]
        assert "workspace_access.runs" in diff_fields

        runs_diff = next(d for d in comparison.diffs if d.field == "workspace_access.runs")
        assert runs_diff.value_a == "apply"
        assert runs_diff.value_b == "read"

    def test_different_access_level_shows_diff(self):
        client = _make_client_mock()
        raw_a = [
            _make_team_project_access_response("tprj-111", "team-aaa", "prj-001", access="admin")
        ]
        raw_b = [
            _make_team_project_access_response("tprj-222", "team-bbb", "prj-002", access="read")
        ]
        client.paginate.side_effect = [iter(raw_a), iter(raw_b)]

        api = TeamsAPI(client)
        comparison = api.compare_project_access(
            project_id_a="prj-001",
            team_id_a="team-aaa",
            project_id_b="prj-002",
            team_id_b="team-bbb",
        )

        assert comparison.identical is False
        assert any(d.field == "access" for d in comparison.diffs)


# ---------------------------------------------------------------------------
# TeamProjectAccessComparison model
# ---------------------------------------------------------------------------


class TestTeamProjectAccessComparison:
    def _make_access(
        self, record_id: str, team_id: str, project_id: str, **kwargs
    ) -> TeamProjectAccess:
        return TeamProjectAccess.from_api_response(
            _make_team_project_access_response(record_id, team_id, project_id, **kwargs)
        )

    def test_identical_access_is_identical(self):
        a = self._make_access("tprj-001", "team-aaa", "prj-001")
        b = self._make_access("tprj-002", "team-bbb", "prj-002")

        result = TeamProjectAccessComparison.compare(a, b)

        assert result.identical is True
        assert result.diffs == []

    def test_runs_diff_detected(self):
        a = self._make_access("tprj-001", "team-aaa", "prj-001", runs="apply")
        b = self._make_access("tprj-002", "team-bbb", "prj-002", runs="read")

        result = TeamProjectAccessComparison.compare(a, b)

        assert result.identical is False
        fields = [d.field for d in result.diffs]
        assert "workspace_access.runs" in fields

    def test_multiple_diffs_all_reported(self):
        a = self._make_access("tprj-001", "team-aaa", "prj-001", access="admin", runs="apply")
        b = self._make_access("tprj-002", "team-bbb", "prj-002", access="read", runs="read")

        result = TeamProjectAccessComparison.compare(a, b)

        assert result.identical is False
        fields = [d.field for d in result.diffs]
        assert "access" in fields
        assert "workspace_access.runs" in fields

    def test_diff_values_are_correct(self):
        a = self._make_access("tprj-001", "team-aaa", "prj-001", runs="apply")
        b = self._make_access("tprj-002", "team-bbb", "prj-002", runs="plan")

        result = TeamProjectAccessComparison.compare(a, b)

        runs_diff = next(d for d in result.diffs if d.field == "workspace_access.runs")
        assert runs_diff.value_a == "apply"
        assert runs_diff.value_b == "plan"
