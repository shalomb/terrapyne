"""UAT test fixtures — shared, session-scoped, cached.

All TFC API calls happen once during fixture setup, then tests
read from cached results. This keeps UAT runtime under 30s.
"""

import os

import pytest

from terrapyne import TFCClient

TFC_ORG = os.environ.get("TFC_ORG", "Takeda")


@pytest.fixture(scope="session")
def tfc_org():
    return TFC_ORG


@pytest.fixture(scope="session")
def client():
    """Single TFC client for the entire UAT session."""
    with TFCClient(organization=TFC_ORG) as c:
        yield c


@pytest.fixture(scope="session")
def workspaces(client):
    """Fetch a small batch of workspaces once, using wildcard search."""
    ws_iter, total = client.workspaces.list(organization=TFC_ORG, search="*shalomb*")
    ws_list = []
    for ws in ws_iter:
        ws_list.append(ws)
        if len(ws_list) >= 3:
            break
    if not ws_list:
        pytest.skip("No workspaces matching '*shalomb*'")
    return ws_list, total


@pytest.fixture(scope="session")
def any_workspace(workspaces):
    """First workspace from the cached batch."""
    return workspaces[0][0]


@pytest.fixture(scope="session")
def workspace_variables(client, any_workspace):
    """Variables for the test workspace, fetched once."""
    return client.workspaces.get_variables(any_workspace.id)


@pytest.fixture(scope="session")
def workspace_runs(client, any_workspace):
    """Runs for the test workspace, fetched once."""
    runs, total = client.runs.list(any_workspace.id, limit=5)
    return runs, total


@pytest.fixture(scope="session")
def any_run(workspace_runs):
    """First run, or skip if none."""
    runs, _ = workspace_runs
    if not runs:
        pytest.skip("No runs in workspace")
    return runs[0]


@pytest.fixture(scope="session")
def state_versions(client, any_workspace, tfc_org):
    """State versions for the test workspace, fetched once."""
    versions, total = client.state_versions.list(
        any_workspace.id, organization=tfc_org, workspace_name=any_workspace.name, limit=3
    )
    return versions, total


@pytest.fixture(scope="session")
def current_state(client, any_workspace):
    """Current state version, or skip if none."""
    try:
        return client.state_versions.get_current(any_workspace.id)
    except Exception:
        pytest.skip("No state versions in workspace")


@pytest.fixture(scope="session")
def projects(client, tfc_org):
    """Fetch projects using search."""
    proj_iter, total = client.projects.list(organization=tfc_org, search="*DAT*")
    proj_list = []
    for p in proj_iter:
        proj_list.append(p)
        if len(proj_list) >= 3:
            break
    if not proj_list:
        pytest.skip("No projects matching '*DAT*'")
    return proj_list, total


@pytest.fixture(scope="session")
def teams(client, tfc_org):
    """Fetch teams using server-side search."""
    teams_iter, total = client.teams.list_teams(organization=tfc_org, search="okta-terraform")
    team_list = []
    for t in teams_iter:
        team_list.append(t)
        if len(team_list) >= 3:
            break
    if not team_list:
        pytest.skip("No teams matching 'okta-terraform'")
    return team_list, total
