"""UAT tests — real TFC API calls, read-only.

Run with: make test-uat
Requires: TFC credentials in ~/.terraform.d/credentials.tfrc.json or TFC_TOKEN env var.

All expensive API calls are in session-scoped fixtures (conftest.py).
Tests here just assert on the cached results — no extra API calls.
"""

import pytest

pytestmark = pytest.mark.uat


class TestClientConnectivity:
    def test_client_connects(self, client):
        assert client.base_url.startswith("https://")

    def test_list_workspaces(self, workspaces):
        ws_list, total = workspaces
        assert len(ws_list) >= 1
        assert total is not None and total >= 1

    def test_list_projects(self, projects):
        proj_list, _total = projects
        assert len(proj_list) >= 1


class TestWorkspaceOperations:
    def test_get_workspace(self, client, any_workspace):
        ws = client.workspaces.get_by_id(any_workspace.id)
        assert ws.id == any_workspace.id
        assert ws.name == any_workspace.name

    def test_workspace_has_expected_fields(self, any_workspace):
        assert any_workspace.id.startswith("ws-")
        assert any_workspace.name
        assert any_workspace.terraform_version

    def test_get_variables(self, workspace_variables):
        assert isinstance(workspace_variables, list)


class TestRunOperations:
    def test_list_runs(self, workspace_runs):
        runs, _ = workspace_runs
        assert isinstance(runs, list)
        if runs:
            assert runs[0].id.startswith("run-")

    def test_get_run(self, client, any_run):
        run = client.runs.get(any_run.id)
        assert run.id == any_run.id


class TestStateVersionOperations:
    def test_list_state_versions(self, state_versions):
        versions, _ = state_versions
        assert isinstance(versions, list)
        if versions:
            assert versions[0].id.startswith("sv-")
            assert versions[0].serial >= 0

    def test_get_current_state(self, current_state):
        assert current_state.id.startswith("sv-")
        assert current_state.download_url


class TestTeamOperations:
    def test_list_teams(self, teams):
        team_list, _ = teams
        assert len(team_list) >= 1
        assert team_list[0].id.startswith("team-")


class TestCLISmoke:
    """Smoke test CLI commands against real API."""

    def test_workspace_list(self, tfc_org):
        from typer.testing import CliRunner

        from terrapyne.cli.main import app

        result = CliRunner().invoke(
            app, ["workspace", "list", "-o", tfc_org, "--search", "*shalomb*"]
        )
        assert result.exit_code == 0

    def test_project_list(self, tfc_org):
        from typer.testing import CliRunner

        from terrapyne.cli.main import app

        result = CliRunner().invoke(app, ["project", "list", "-o", tfc_org, "--search", "DAT"])
        assert result.exit_code == 0
