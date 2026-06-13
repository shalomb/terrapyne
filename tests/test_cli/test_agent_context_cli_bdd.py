"""BDD steps for adaptive CLI output based on agent context."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.run import Run, RunStatus
from terrapyne.models.team import Team
from terrapyne.models.workspace import Workspace

runner = CliRunner()
runner.mix_stderr = True
runner.mix_stderr = True

# ---------------------------------------------------------------------------
# Scenario bindings
# ---------------------------------------------------------------------------


@scenario(
    "../features/agent_context_cli.feature",
    "workspace list defaults to JSON when CLAUDECODE is set",
)
def test_agent_ws_list_json():
    pass


@scenario(
    "../features/agent_context_cli.feature",
    "workspace show defaults to JSON when CLAUDECODE is set",
)
def test_agent_ws_show_json():
    pass


@scenario("../features/agent_context_cli.feature", "run list defaults to JSON when running in CI")
def test_ci_run_list_json():
    pass


@scenario(
    "../features/agent_context_cli.feature", "team list defaults to JSON when stdout is a pipe"
)
def test_pipe_team_list_json():
    pass


@scenario("../features/agent_context_cli.feature", "workspace list renders a table for human users")
def test_human_ws_list_table():
    pass


@scenario("../features/agent_context_cli.feature", "human can request JSON with --format json")
def test_human_explicit_json():
    pass


@scenario("../features/agent_context_cli.feature", "agent can request table with --format table")
def test_agent_explicit_table():
    pass


@scenario("../features/agent_context_cli.feature", "--debug prints the agent context reason")
def test_debug_reason():
    pass


# ---------------------------------------------------------------------------
# Given — context fixtures
# ---------------------------------------------------------------------------


@given("the CLI is running under a Claude Code agent context", target_fixture="agent_env")
def claude_agent_env():
    """Simulate CLAUDECODE=1 with stdout NOT a tty (typical tool-call context)."""
    return {"CLAUDECODE": "1"}


@given("the CLI is running in a CI pipeline", target_fixture="agent_env")
def ci_env():
    return {"CI": "true"}


@given("the CLI is running with stdout piped", target_fixture="agent_env")
def piped_env():
    """No agent env var — detection relies purely on isatty=False."""
    return {}


@given("the CLI is running as a human in an interactive terminal", target_fixture="agent_env")
def human_env():
    return None  # no agent env vars; isatty=True will be set in when-steps


# ---------------------------------------------------------------------------
# Given — data fixtures
# ---------------------------------------------------------------------------


@given("workspaces exist in the organization", target_fixture="mock_client")
def workspaces_exist():
    m = MagicMock()
    m.workspaces.list.return_value = (
        iter(
            [
                Workspace.model_construct(
                    id="ws-abc",
                    name="my-app-dev",
                    terraform_version="1.9.0",
                    created_at=None,
                    updated_at=None,
                    auto_apply=False,
                    execution_mode="remote",
                    locked=False,
                    tag_names=[],
                    project_id=None,
                )
            ]
        ),
        1,
    )
    return m


@given(parsers.parse('workspace "{name}" exists'), target_fixture="mock_client")
def workspace_named(name):
    m = MagicMock()
    m.workspaces.get.return_value = Workspace.model_construct(
        id="ws-abc",
        name=name,
        terraform_version="1.9.0",
        created_at=None,
        updated_at=None,
        auto_apply=False,
        execution_mode="remote",
        locked=False,
        tag_names=[],
        project_id=None,
    )
    m.workspaces.get_variables.return_value = []
    m.vcs.get_workspace_vcs.return_value = None
    m.runs.list.return_value = ([], 0)
    return m


@given("a workspace with runs exists", target_fixture="mock_client")
def workspace_with_runs():
    m = MagicMock()
    m.workspaces.get.return_value = Workspace.model_construct(id="ws-abc", name="my-app-dev")
    m.runs.list.return_value = (
        [
            Run.model_construct(
                id="run-xyz",
                status=RunStatus("applied"),
                message="deploy",
                created_at=None,
                updated_at=None,
                additions=1,
                changes=0,
                destructions=0,
                workspace_id="ws-abc",
            )
        ],
        1,
    )
    return m


@given("teams exist in the organization", target_fixture="mock_client")
def teams_exist():
    m = MagicMock()
    m.teams.list_teams.return_value = (
        iter([Team.model_construct(id="team-1", name="devs", created_at=None)]),
        1,
    )
    return m


# ---------------------------------------------------------------------------
# When — invoke CLI with agent or human context injected
# ---------------------------------------------------------------------------


def _invoke_as_agent(env: dict, args: list[str]) -> object:
    """Invoke the CLI simulating an agent: env vars set, stdout NOT a tty."""
    with (
        patch("terrapyne.cli.workspace_cmd.validate_context") as v,
        patch("terrapyne.cli.run_cmd.validate_context") as rv,
        patch("terrapyne.cli.team_cmd.validate_context") as tv,
        patch("terrapyne.cli.agent_context.detect") as detect,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        from terrapyne.cli.agent_context import AgentContext

        reason = next(iter(f"{k}={v!r}" for k, v in env.items()), "stdout is not a tty")
        detect.return_value = AgentContext(is_agent=True, reason=reason)
        v.return_value = ("test-org", "my-app-dev")
        rv.return_value = ("test-org", "my-app-dev")
        tv.return_value = ("test-org", None)
        c.return_value.__enter__ = lambda s: c.return_value
        c.return_value.__exit__ = MagicMock(return_value=False)
        return args, detect, v, rv, tv, c


def _invoke_as_human(args: list[str]) -> object:
    """Invoke the CLI simulating a human: no agent env vars, stdout IS a tty."""
    with (
        patch("terrapyne.cli.workspace_cmd.validate_context") as v,
        patch("terrapyne.cli.run_cmd.validate_context") as rv,
        patch("terrapyne.cli.team_cmd.validate_context") as tv,
        patch("terrapyne.cli.agent_context.detect") as detect,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        from terrapyne.cli.agent_context import AgentContext

        detect.return_value = AgentContext(is_agent=False, reason=None)
        v.return_value = ("test-org", "my-app-dev")
        rv.return_value = ("test-org", "my-app-dev")
        tv.return_value = ("test-org", None)
        c.return_value.__enter__ = lambda s: c.return_value
        c.return_value.__exit__ = MagicMock(return_value=False)
        return args, detect, v, rv, tv, c


@when('I run "workspace list" without a format flag', target_fixture="cli_result")
def run_ws_list_no_flag(mock_client, agent_env):
    from terrapyne.cli.agent_context import AgentContext

    is_agent = agent_env is not None
    reason = (
        next(iter(f"{k}={v!r}" for k, v in (agent_env or {}).items()), "stdout is not a tty")
        if is_agent
        else None
    )
    with (
        patch("terrapyne.cli.workspace_cmd.validate_context") as v,
        patch("terrapyne.cli.agent_context.detect") as detect,
        patch("terrapyne.cli.output_helpers.configure_for_agent_context") as cfgac,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        ctx_obj = AgentContext(is_agent=is_agent, reason=reason)
        detect.return_value = ctx_obj
        cfgac.return_value = ctx_obj
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__ = lambda s: mock_client
        c.return_value.__exit__ = MagicMock(return_value=False)
        return runner.invoke(app, ["workspace", "list", "-o", "test-org"])


@when('I run "workspace show" without a format flag', target_fixture="cli_result")
def run_ws_show_no_flag(mock_client, agent_env):
    from terrapyne.cli.agent_context import AgentContext

    is_agent = agent_env is not None
    reason = (
        next(iter(f"{k}={v!r}" for k, v in (agent_env or {}).items()), None) if is_agent else None
    )
    with (
        patch("terrapyne.cli.workspace_cmd.validate_context") as v,
        patch("terrapyne.cli.agent_context.detect") as detect,
        patch("terrapyne.cli.output_helpers.configure_for_agent_context") as cfgac,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        ctx_obj = AgentContext(is_agent=is_agent, reason=reason)
        detect.return_value = ctx_obj
        cfgac.return_value = ctx_obj
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__ = lambda s: mock_client
        c.return_value.__exit__ = MagicMock(return_value=False)
        return runner.invoke(app, ["workspace", "show", "my-app-dev", "-o", "test-org"])


@when('I run "run list" without a format flag', target_fixture="cli_result")
def run_run_list_no_flag(mock_client, agent_env):
    from terrapyne.cli.agent_context import AgentContext

    is_agent = agent_env is not None
    reason = (
        next(iter(f"{k}={v!r}" for k, v in (agent_env or {}).items()), None) if is_agent else None
    )
    with (
        patch("terrapyne.cli.run_cmd.validate_context") as v,
        patch("terrapyne.cli.agent_context.detect") as detect,
        patch("terrapyne.cli.output_helpers.configure_for_agent_context") as cfgac,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        ctx_obj = AgentContext(is_agent=is_agent, reason=reason)
        detect.return_value = ctx_obj
        cfgac.return_value = ctx_obj
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__ = lambda s: mock_client
        c.return_value.__exit__ = MagicMock(return_value=False)
        return runner.invoke(app, ["run", "list", "-w", "my-app-dev", "-o", "test-org"])


@when('I run "team list" without a format flag', target_fixture="cli_result")
def run_team_list_no_flag(mock_client, agent_env):
    from terrapyne.cli.agent_context import AgentContext

    # pipe context: agent_env={} but is_agent=True via isatty=False
    with (
        patch("terrapyne.cli.team_cmd.validate_context") as v,
        patch("terrapyne.cli.agent_context.detect") as detect,
        patch("terrapyne.cli.output_helpers.configure_for_agent_context") as cfgac,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        ctx_obj = AgentContext(is_agent=True, reason="stdout is not a tty")
        detect.return_value = ctx_obj
        cfgac.return_value = ctx_obj
        v.return_value = ("test-org", None)
        c.return_value.__enter__ = lambda s: mock_client
        c.return_value.__exit__ = MagicMock(return_value=False)
        return runner.invoke(app, ["team", "list", "-o", "test-org"])


@when(parsers.parse('I run "workspace list" with "{flags}"'), target_fixture="cli_result")
def run_ws_list_with_flag(mock_client, agent_env, flags):
    from terrapyne.cli.agent_context import AgentContext

    is_agent = agent_env is not None
    reason = (
        next(iter(f"{k}={v!r}" for k, v in (agent_env or {}).items()), None) if is_agent else None
    )
    with (
        patch("terrapyne.cli.workspace_cmd.validate_context") as v,
        patch("terrapyne.cli.agent_context.detect") as detect,
        patch("terrapyne.cli.output_helpers.configure_for_agent_context") as cfgac,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        ctx_obj = AgentContext(is_agent=is_agent, reason=reason)
        detect.return_value = ctx_obj
        cfgac.return_value = ctx_obj
        v.return_value = ("test-org", "my-app-dev")
        c.return_value.__enter__ = lambda s: mock_client
        c.return_value.__exit__ = MagicMock(return_value=False)
        extra_args = flags.split()
        # Global flags (--debug, --quiet) must precede the subcommand group
        global_flags = [f for f in extra_args if f.startswith("--") and f in ("--debug", "--quiet")]
        cmd_flags = [f for f in extra_args if f not in global_flags]
        return runner.invoke(
            app, [*global_flags, "workspace", "list", "-o", "test-org", *cmd_flags]
        )


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the output is valid JSON")
def output_is_json(cli_result):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.output}"
    try:
        json.loads(cli_result.output)
    except json.JSONDecodeError as e:
        pytest.fail(f"Output is not valid JSON: {e}\nOutput was:\n{cli_result.output}")


@then("the output is not JSON")
def output_is_not_json(cli_result):
    assert cli_result.exit_code == 0, f"Exit {cli_result.exit_code}: {cli_result.output}"
    try:
        json.loads(cli_result.output)
        pytest.fail(f"Expected non-JSON output but got valid JSON:\n{cli_result.output}")
    except json.JSONDecodeError:
        pass  # expected


@then(parsers.parse('each workspace has an "{key1}" and "{key2}"'))
def workspaces_have_keys(cli_result, key1, key2):
    data = json.loads(cli_result.output)
    assert isinstance(data, list), f"Expected a JSON array, got: {type(data)}"
    for item in data:
        assert key1 in item, f"Missing key '{key1}' in {item}"
        assert key2 in item, f"Missing key '{key2}' in {item}"


@then(parsers.parse('each run has an "{key1}" and "{key2}"'))
def runs_have_keys(cli_result, key1, key2):
    data = json.loads(cli_result.output)
    assert isinstance(data, list)
    for item in data:
        assert key1 in item
        assert key2 in item


@then(parsers.parse('each team has an "{key1}" and "{key2}"'))
def teams_have_keys(cli_result, key1, key2):
    data = json.loads(cli_result.output)
    assert isinstance(data, list)
    for item in data:
        assert key1 in item
        assert key2 in item


@then(parsers.parse('the result has key "{key}"'))
def result_has_key(cli_result, key):
    data = json.loads(cli_result.output)
    assert isinstance(data, dict), f"Expected JSON object, got {type(data)}"
    assert key in data, f"Missing key '{key}' in {data.keys()}"


@then("the output contains the workspace name")
def output_contains_ws_name(cli_result):
    assert "my-app-dev" in cli_result.output, f"Workspace name not found in:\n{cli_result.output}"


@then(parsers.parse('the output contains "{text}"'))
def output_contains(cli_result, text):
    assert text in cli_result.output, f"{text!r} not found in output:\n{cli_result.output}"
