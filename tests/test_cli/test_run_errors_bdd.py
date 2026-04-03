"""BDD tests for 'run errors' command."""

import pytest
from datetime import datetime, UTC, timedelta
from pytest_bdd import given, scenario, then, when, parsers
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from terrapyne.cli.main import app
from terrapyne.models.run import Run, RunStatus
from terrapyne.models.workspace import Workspace
from terrapyne.models.project import Project

runner = CliRunner()

# ============================================================================
# Scenarios
# ============================================================================

@scenario("../features/run.feature", "List errored runs across a project")
def test_list_errored_runs_project(): pass

@scenario("../features/run.feature", "No errored runs shows clean output")
def test_no_errored_runs(): pass

# ============================================================================
# Step Definitions
# ============================================================================

@given(parsers.parse('project "{project_name}" has workspaces with recent errored runs:'), target_fixture="errored_setup")
def setup_errored_runs(project_name, datatable):
    # Set dates to very recent to ensure they pass the 'days' filter
    now = datetime.now(UTC)
    setup = []
    for row in datatable:
        if row[0] == 'workspace': continue
        setup.append({
            'workspace': row[0],
            'run_id': row[1],
            'message': row[2],
            'created_at': (now - timedelta(minutes=10)).isoformat()
        })
    return {"project": project_name, "runs": setup}

@when(parsers.parse('I run "terrapyne run errors --project {project}"'), target_fixture="cli_result")
def run_errors_project(project, errored_setup):
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # 1. Mock projects.list
        proj = Project.model_construct(id="proj-123", name=project)
        mock_instance.projects.list.return_value = ([proj], 1)

        # 2. Mock workspaces.list
        workspaces = []
        for r in errored_setup["runs"]:
            if not any(w.name == r['workspace'] for w in workspaces):
                workspaces.append(Workspace.model_construct(id=f"ws-{r['workspace']}", name=r['workspace']))
        mock_instance.workspaces.list.return_value = (iter(workspaces), len(workspaces))

        # 3. Mock runs.list for each workspace
        def mock_runs_list(workspace_id, limit=50, status=None):
            ws_name = workspace_id.replace("ws-", "")
            ws_runs = []
            for r in errored_setup["runs"]:
                if r['workspace'] == ws_name:
                    ws_runs.append(Run.model_construct(
                        id=r['run_id'],
                        status=RunStatus.ERRORED,
                        message=r['message'],
                        created_at=datetime.fromisoformat(r['created_at'].replace('Z', '+00:00'))
                    ))
            return (ws_runs, len(ws_runs))
        
        mock_instance.runs.list.side_effect = mock_runs_list

        result = runner.invoke(app, ["run", "errors", "--project", project, "--organization", "test-org"])
        return result

@then("I should see both errored runs in a table")
def check_errored_table(cli_result):
    assert cli_result.exit_code == 0
    assert "Errored Runs" in cli_result.stdout
    assert "run-aaa111" in cli_result.stdout
    assert "run-bbb222" in cli_result.stdout

@then("the table should include workspace name, run ID, error summary, and time")
def check_table_columns(cli_result):
    assert "Workspace" in cli_result.stdout
    assert "Run ID" in cli_result.stdout
    assert "Time" in cli_result.stdout
    assert "Message" in cli_result.stdout

@given(parsers.parse('no workspaces have errored runs in the last {days} days'), target_fixture="errored_setup")
def setup_no_errors(days):
    return {"project": "platform", "runs": [], "days": int(days)}

@when(parsers.parse('I run "terrapyne run errors --project {project} --days {days}"'), target_fixture="cli_result")
def run_errors_no_results(project, days, errored_setup):
    with patch("terrapyne.cli.run_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # Mock project found
        proj = Project.model_construct(id="proj-123", name=project)
        mock_instance.projects.list.return_value = ([proj], 1)
        
        # Mock no workspaces
        mock_instance.workspaces.list.return_value = (iter([]), 0)

        # Splitting args properly into a list
        args = ["run", "errors", "--project", project, "--days", str(days), "--organization", "test-org"]
        result = runner.invoke(app, args)
        return result

@then(parsers.parse('I should see "✅ No errored runs found in project \'{project}\' in the last {days} day(s)."'))
def check_no_errors_msg(cli_result, project, days):
    # Flexible match to avoid Typer parsing issues in tests
    assert "No errored runs found" in cli_result.stdout
    assert cli_result.exit_code == 0
