"""BDD step definitions for Agent Experience (AX) CLI features.

Covers AX1 (ID resolver), AX2 (latest run lookups), AX3 (trigger+wait),
AX4 (state output extraction), AX5 (JSON mutations), AX6 (idempotent create).
"""

import fnmatch
import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.run import Run
from terrapyne.models.workspace import Workspace
from tests.fixtures.factories import run_response, workspace_response

runner = CliRunner()

FEATURE = "../features/agent_experience.feature"


# ===========================================================================
# Scenario declarations
# ===========================================================================


@scenario(FEATURE, "Resolve workspace ID without jq")
def test_ax1_workspace_id():
    pass


@scenario(FEATURE, "Resolve project ID without jq")
def test_ax1_project_id():
    pass


@scenario(FEATURE, "Resolving ID for a non-existent workspace exits non-zero")
def test_ax1_workspace_id_not_found():
    pass


@scenario(FEATURE, "Show logs for the latest run without knowing its ID")
def test_ax2_run_logs_latest():
    pass


@scenario(FEATURE, "Show run detail for the latest run without knowing its ID")
def test_ax2_run_show_latest():
    pass


@scenario(FEATURE, "Trigger a run and wait silently for completion")
def test_ax3_trigger_wait_success():
    pass


@scenario(FEATURE, "Trigger and wait exits non-zero when run errors")
def test_ax3_trigger_wait_error():
    pass


@scenario(FEATURE, "Extract a single state output value")
def test_ax4_state_output():
    pass


@scenario(FEATURE, "Extracting a missing state output exits non-zero")
def test_ax4_state_output_missing():
    pass


@scenario(FEATURE, "workspace create emits JSON with workspace ID")
def test_ax5_workspace_create_json():
    pass


@scenario(FEATURE, "workspace clone emits JSON with new workspace ID")
def test_ax5_workspace_clone_json():
    pass


@scenario(FEATURE, "run trigger emits JSON with run ID")
def test_ax5_run_trigger_json():
    pass


@scenario(FEATURE, "workspace create with --ignore-exists succeeds when workspace already present")
def test_ax6_ignore_exists_success():
    pass


@scenario(FEATURE, "workspace create without --ignore-exists fails when workspace exists")
def test_ax6_conflict_fails():
    pass


# ===========================================================================
# Shared Givens
# ===========================================================================


@given("a terraform cloud organization is accessible")
def tfc_org_accessible():
    pass


@given(parsers.parse('a workspace "{name}" exists'), target_fixture="workspace_ctx")
def workspace_ctx(name):
    return {"name": name, "id": "ws-abc123"}


@given(parsers.parse('a project "{name}" exists with id "{proj_id}"'), target_fixture="project_ctx")
def project_ctx(name, proj_id):
    return {"name": name, "id": proj_id}


@given(
    parsers.parse('a workspace "{name}" is ready for operations'), target_fixture="workspace_ctx"
)
def workspace_ready_ctx(name):
    return {"name": name, "id": "ws-ready123"}


@given(parsers.parse('a workspace "{name}" has runs'), target_fixture="workspace_ctx")
def workspace_has_runs_ctx(name):
    return {"name": name, "id": "ws-runs123"}


@given(
    parsers.parse('a workspace "{name}" has a most recent run "{run_id}"'),
    target_fixture="workspace_ctx",
)
def workspace_latest_run_ctx(name, run_id):
    return {"name": name, "id": "ws-latest123", "latest_run_id": run_id}


@given(parsers.parse('a workspace "{name}" already exists'), target_fixture="workspace_ctx")
def workspace_already_exists_ctx(name):
    return {"name": name, "id": "ws-exists123"}


@given(
    parsers.parse('a workspace with output "{key}" = "{value}"'),
    target_fixture="output_ctx",
)
def output_ctx(key, value):
    return {"key": key, "value": value}


@given(parsers.parse('a workspace with no output named "{key}"'), target_fixture="output_ctx")
def no_output_ctx(key):
    return {"key": key, "value": None}


# ===========================================================================
# AX1 — Whens
# ===========================================================================


@when(parsers.parse('I run "tfc workspace id {name}"'), target_fixture="cli_result")
def run_workspace_id(name, workspace_ctx):
    ws = Workspace.from_api_response(workspace_response(id=workspace_ctx["id"], name=name)["data"])
    with patch("terrapyne.cli.workspace_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.return_value = ws
        return runner.invoke(app, ["workspace", "id", name, "--organization", "test-org"])


@when("I resolve the id of a workspace that does not exist", target_fixture="cli_result")
def run_workspace_id_not_found():
    from terrapyne.core.exceptions import TFCNotFoundError

    with patch("terrapyne.cli.workspace_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.side_effect = TFCNotFoundError("not found")
        return runner.invoke(
            app, ["workspace", "id", "no-such-workspace", "--organization", "test-org"]
        )


@when(parsers.parse('I run "tfc project id {name}"'), target_fixture="cli_result")
def run_project_id(name, project_ctx):
    from terrapyne.models.project import Project

    proj = MagicMock(spec=Project)
    proj.id = project_ctx["id"]
    proj.name = name
    with patch("terrapyne.cli.project_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.projects.get_by_name.return_value = proj
        return runner.invoke(app, ["project", "id", name, "--organization", "test-org"])


# ===========================================================================
# AX2 — Whens
# ===========================================================================


@when(
    parsers.parse('I run "tfc run logs --workspace {name} --latest"'),
    target_fixture="cli_result",
)
def run_logs_latest(name, workspace_ctx):
    ws = Workspace.from_api_response(workspace_response(id=workspace_ctx["id"], name=name)["data"])
    run = Run.from_api_response(run_response(id="run-latest-001")["data"])
    with patch("terrapyne.cli.run_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.return_value = ws
        mock_client.runs.list.return_value = (iter([run]), 1)
        mock_client.runs.get.return_value = run
        mock_client.runs.get_plan_logs.return_value = "Plan log output"
        mock_client.runs.get_plan.return_value = MagicMock(log_read_url=None)
        return runner.invoke(
            app,
            ["run", "logs", "--workspace", name, "--latest", "--organization", "test-org"],
        )


@when(
    parsers.parse('I run "tfc run show --workspace {name} --latest"'),
    target_fixture="cli_result",
)
def run_show_latest(name, workspace_ctx):
    ws = Workspace.from_api_response(workspace_response(id=workspace_ctx["id"], name=name)["data"])
    latest_run_id = workspace_ctx.get("latest_run_id", "run-latest-001")
    run = Run.from_api_response(run_response(id=latest_run_id)["data"])
    with patch("terrapyne.cli.run_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.return_value = ws
        mock_client.runs.list.return_value = (iter([run]), 1)
        mock_client.runs.get.return_value = run
        return runner.invoke(
            app,
            ["run", "show", "--workspace", name, "--latest", "--organization", "test-org"],
        )


# ===========================================================================
# AX3 — Whens
# ===========================================================================


@when(
    parsers.parse('I trigger a run for "{name}" with "--wait"'),
    target_fixture="cli_result",
)
def trigger_wait_success(name, workspace_ctx):
    ws = Workspace.from_api_response(workspace_response(id=workspace_ctx["id"], name=name)["data"])
    run = Run.from_api_response(run_response(id="run-wait-001", status="applied")["data"])
    with patch("terrapyne.cli.run_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.return_value = ws
        mock_client.runs.get_active_runs.return_value = []
        mock_client.runs.create.return_value = run
        mock_client.runs.poll_until_complete.return_value = run
        return runner.invoke(
            app,
            ["--quiet", "run", "trigger", name, "--wait", "--organization", "test-org"],
        )


@when(
    parsers.parse('I trigger a run for "{name}" with "--wait" and the run errors'),
    target_fixture="cli_result",
)
def trigger_wait_error(name, workspace_ctx):
    ws = Workspace.from_api_response(workspace_response(id=workspace_ctx["id"], name=name)["data"])
    pending = Run.from_api_response(run_response(id="run-err-001", status="pending")["data"])
    errored = Run.from_api_response(run_response(id="run-err-001", status="errored")["data"])
    with patch("terrapyne.cli.run_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.return_value = ws
        mock_client.runs.get_active_runs.return_value = []
        mock_client.runs.create.return_value = pending
        mock_client.runs.poll_until_complete.return_value = errored
        return runner.invoke(
            app,
            ["--quiet", "run", "trigger", name, "--wait", "--organization", "test-org"],
        )


# ===========================================================================
# AX4 — Whens
# ===========================================================================


@when(
    parsers.parse('I run "tfc state output {workspace} {key}"'),
    target_fixture="cli_result",
)
def run_state_output(workspace, key, output_ctx):
    ws = Workspace.from_api_response(workspace_response(name=workspace)["data"])
    sv = MagicMock()
    sv.id = "sv-abc123"

    if output_ctx["value"] is not None:
        mock_output = MagicMock()
        mock_output.name = key
        mock_output.value = output_ctx["value"]
        mock_output.sensitive = False
        outputs = [mock_output]
    else:
        outputs = []

    with patch("terrapyne.cli.state_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.return_value = ws
        mock_client.state_versions.get_current.return_value = sv
        mock_client.state_versions.list_outputs.return_value = outputs
        return runner.invoke(
            app,
            ["state", "output", workspace, key, "--organization", "test-org"],
        )


# ===========================================================================
# AX5 — Whens
# ===========================================================================


@when(
    parsers.parse('I create workspace "{name}" with "--format json"'),
    target_fixture="cli_result",
)
def create_workspace_json(name):
    ws = Workspace.from_api_response(workspace_response(id="ws-newws123", name=name)["data"])
    with patch("terrapyne.cli.workspace_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.create.return_value = ws
        return runner.invoke(
            app,
            ["workspace", "create", name, "--format", "json", "--organization", "test-org"],
        )


@when(
    parsers.parse('I clone "{src}" to "{dst}" with "--format json"'),
    target_fixture="cli_result",
)
def clone_workspace_json(src, dst, workspace_ctx):
    src_ws = Workspace.from_api_response(
        workspace_response(id=workspace_ctx["id"], name=src)["data"]
    )
    dst_ws = Workspace.from_api_response(workspace_response(id="ws-newclone1", name=dst)["data"])
    with patch("terrapyne.cli.workspace_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.return_value = src_ws
        with patch("terrapyne.api.workspace_clone.CloneWorkspaceAPI") as mock_clone_cls:
            mock_clone = MagicMock()
            mock_clone_cls.return_value = mock_clone
            mock_clone.clone.return_value = {
                "status": "success",
                "message": "Cloned successfully",
                "workspace": dst_ws,
                "results": {},
            }
            return runner.invoke(
                app,
                ["workspace", "clone", src, dst, "--format", "json", "--organization", "test-org"],
            )


@when(
    parsers.parse('I trigger a run for "{name}" with "--format json"'),
    target_fixture="cli_result",
)
def trigger_run_json(name, workspace_ctx):
    ws = Workspace.from_api_response(workspace_response(id=workspace_ctx["id"], name=name)["data"])
    run = Run.from_api_response(run_response(id="run-json001", status="pending")["data"])
    with patch("terrapyne.cli.run_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.get.return_value = ws
        mock_client.runs.get_active_runs.return_value = []
        mock_client.runs.create.return_value = run
        return runner.invoke(
            app,
            [
                "run",
                "trigger",
                name,
                "--no-wait",
                "--format",
                "json",
                "--organization",
                "test-org",
            ],
        )


# ===========================================================================
# AX6 — Whens
# ===========================================================================


@when(
    parsers.parse('I create workspace "{name}" with "--ignore-exists"'),
    target_fixture="cli_result",
)
def create_workspace_ignore_exists(name, workspace_ctx):
    from terrapyne.core.exceptions import TFCConflictError

    existing = Workspace.from_api_response(
        workspace_response(id=workspace_ctx["id"], name=name)["data"]
    )
    with patch("terrapyne.cli.workspace_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.create.side_effect = TFCConflictError("already exists")
        mock_client.workspaces.get.return_value = existing
        return runner.invoke(
            app,
            ["workspace", "create", name, "--ignore-exists", "--organization", "test-org"],
        )


@when(
    parsers.parse('I create workspace "{name}" without "--ignore-exists"'),
    target_fixture="cli_result",
)
def create_workspace_no_ignore(name, workspace_ctx):
    from terrapyne.core.exceptions import TFCConflictError

    with patch("terrapyne.cli.workspace_cmd.get_client") as mock_gc:
        mock_client = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_client
        mock_client.workspaces.create.side_effect = TFCConflictError("already exists")
        return runner.invoke(
            app,
            ["workspace", "create", name, "--organization", "test-org"],
        )


# ===========================================================================
# Shared Thens
# ===========================================================================


@then(parsers.parse('stdout is exactly "{expected}"'))
def stdout_exactly(cli_result, expected):
    actual = cli_result.output.strip()
    assert actual == expected, f"Expected {expected!r}, got {actual!r}"


@then("there is no extra formatting")
def no_extra_formatting(cli_result):
    output = cli_result.output.strip()
    assert "\n" not in output, f"Unexpected newline in output: {output!r}"


@then("the exit code is 1")
def exit_code_1(cli_result):
    assert cli_result.exit_code == 1, (
        f"Expected exit 1, got {cli_result.exit_code}\nOutput: {cli_result.output}"
    )


@then(parsers.parse('stderr contains "{text}"'))
def stderr_contains(cli_result, text):
    combined = cli_result.output + (cli_result.stderr or "")
    assert text.lower() in combined.lower(), f"Expected {text!r} in output, got: {combined!r}"


@then("the logs for the most recent run are shown")
def logs_shown(cli_result):
    assert cli_result.exit_code == 0, (
        f"Expected exit 0, got {cli_result.exit_code}\n{cli_result.output}"
    )


@then(parsers.parse('the run detail for "{run_id}" is shown'))
def run_detail_shown(cli_result, run_id):
    assert cli_result.exit_code == 0, (
        f"Expected exit 0, got {cli_result.exit_code}\n{cli_result.output}"
    )
    assert run_id in cli_result.output


@then("the command blocks until the run reaches a terminal state")
def command_blocks(cli_result):
    assert cli_result.exit_code == 0


@then("no plan or apply logs are streamed")
def no_logs_streamed(cli_result):
    output = cli_result.output
    assert "Plan:" not in output
    assert "Apply:" not in output


@then("the command exits with code 0 on success")
def exits_0_on_success(cli_result):
    assert cli_result.exit_code == 0, f"Expected 0, got {cli_result.exit_code}\n{cli_result.output}"


@then("the command exits with code 0")
def exits_0(cli_result):
    assert cli_result.exit_code == 0, f"Expected 0, got {cli_result.exit_code}\n{cli_result.output}"


@then("the command exits with code 1")
def exits_1(cli_result):
    assert cli_result.exit_code == 1, f"Expected 1, got {cli_result.exit_code}\n{cli_result.output}"


@then("there is no table formatting")
def no_table_formatting(cli_result):
    output = cli_result.output
    assert "─" not in output
    assert "│" not in output


@then("stdout is valid JSON")
def stdout_is_valid_json(cli_result):
    try:
        json.loads(cli_result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"stdout is not valid JSON: {e}\nOutput: {cli_result.stdout!r}")


@then(parsers.parse('the JSON contains field "{field}" matching "{pattern}"'))
def json_field_matches_pattern(cli_result, field, pattern):
    data = json.loads(cli_result.output)
    assert field in data, f"Field {field!r} not in JSON: {data}"
    assert fnmatch.fnmatch(str(data[field]), pattern), (
        f"Field {field!r}={data[field]!r} does not match {pattern!r}"
    )


@then(parsers.parse('the JSON contains field "{field}" = "{expected}"'))
def json_field_equals(cli_result, field, expected):
    data = json.loads(cli_result.output)
    assert field in data, f"Field {field!r} not in JSON: {data}"
    assert str(data[field]) == expected, (
        f"Field {field!r}: expected {expected!r}, got {data[field]!r}"
    )


@then(parsers.parse('the JSON contains field "{field}"'))
def json_has_field(cli_result, field):
    data = json.loads(cli_result.output)
    assert field in data, f"Field {field!r} not in JSON: {data}"


@then("the existing workspace is returned without creating a duplicate")
def existing_workspace_returned(cli_result):
    assert cli_result.exit_code == 0, f"Expected 0, got {cli_result.exit_code}\n{cli_result.output}"
