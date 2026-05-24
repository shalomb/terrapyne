"""BDD steps for agent context detection."""

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from terrapyne.cli.agent_context import AgentContext, detect

# ---------------------------------------------------------------------------
# Scenario bindings
# ---------------------------------------------------------------------------


@scenario("../features/agent_context.feature", "TERRAPYNE_OUTPUT=json forces agent mode")
def test_terrapyne_output_json():
    pass


@scenario("../features/agent_context.feature", "NO_COLOR signals a non-interactive consumer")
def test_no_color():
    pass


@scenario(
    "../features/agent_context.feature", "TF_IN_AUTOMATION signals a Terraform automation context"
)
def test_tf_in_automation():
    pass


@scenario("../features/agent_context.feature", "CI signals a continuous integration pipeline")
def test_ci():
    pass


@pytest.mark.parametrize(
    "var",
    [
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "CIRCLECI",
        "TRAVIS",
        "BUILDKITE",
        "TEAMCITY_VERSION",
        "BITBUCKET_BUILD_NUMBER",
        "DRONE",
        "SEMAPHORE",
    ],
)
def test_ci_platform_vars(var):
    """Scenario Outline: Common CI platform variables are recognised."""
    result = detect(env={var: "1"}, stdout_isatty=True)
    assert result.is_agent, f"{var} should trigger agent context"
    assert var in result.reason


@scenario("../features/agent_context.feature", "Claude Code is detected by CLAUDECODE")
def test_claudecode():
    pass


@scenario("../features/agent_context.feature", "Gemini CLI is detected by GEMINI_CLI")
def test_gemini_cli():
    pass


@scenario("../features/agent_context.feature", "Antigravity agent is detected by ANTIGRAVITY_AGENT")
def test_antigravity():
    pass


@scenario("../features/agent_context.feature", "Pi coding agent is detected by PI_CODING_AGENT")
def test_pi_coding_agent():
    pass


@scenario("../features/agent_context.feature", "GitHub Copilot is detected by COPILOT_CLI")
def test_copilot_cli():
    pass


@scenario(
    "../features/agent_context.feature", "Amazon Q / Kiro is detected by AWS_EXECUTION_ENV prefix"
)
def test_amazonq():
    pass


@scenario(
    "../features/agent_context.feature",
    "AWS_EXECUTION_ENV for non-agent AWS services is not misclassified",
)
def test_aws_execution_env_not_agent():
    pass


@scenario(
    "../features/agent_context.feature",
    "Stdout piped to another process signals non-interactive use",
)
def test_stdout_pipe():
    pass


@scenario(
    "../features/agent_context.feature",
    "Unknown agent with no recognised env var is caught by pipe detection",
)
def test_unknown_agent_pipe():
    pass


@scenario(
    "../features/agent_context.feature",
    "Interactive terminal with no agent signals is classified as human",
)
def test_human_interactive():
    pass


@scenario(
    "../features/agent_context.feature",
    "CLAUDECODE inherited in a human shell does not misclassify when stdout is a tty",
)
def test_claudecode_inherited_with_tty():
    pass


@scenario(
    "../features/agent_context.feature",
    "TERRAPYNE_OUTPUT=json overrides a clean environment with tty",
)
def test_explicit_override_precedence():
    pass


@scenario(
    "../features/agent_context.feature",
    "TF_IN_AUTOMATION takes precedence over a missing agent var",
)
def test_tf_in_automation_precedence():
    pass


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("the environment is clean", target_fixture="ctx")
def clean_env():
    return {"env": {}, "stdout_isatty": True}


@given(parsers.parse('the environment has "{var}" set to "{value}"'), target_fixture="ctx")
def env_with_var(var, value):
    return {"env": {var: value}, "stdout_isatty": True}


@given(parsers.parse('the environment does not have "{var}"'))
def env_without_var(ctx, var):
    ctx["env"].pop(var, None)


@given("stdout is a tty")
def stdout_is_tty(ctx):
    ctx["stdout_isatty"] = True


@given("stdout is not a tty")
def stdout_is_not_tty(ctx):
    ctx["stdout_isatty"] = False


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when("agent context is detected", target_fixture="result")
def detect_context(ctx):
    return detect(env=ctx["env"], stdout_isatty=ctx["stdout_isatty"])


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("it is identified as an agent")
def identified_as_agent(result: AgentContext):
    assert result.is_agent, f"Expected agent context but got human. reason={result.reason!r}"


@then("it is identified as a human")
def identified_as_human(result: AgentContext):
    assert not result.is_agent, f"Expected human context but got agent. reason={result.reason!r}"


@then(parsers.parse('the reason is "{expected}"'))
def reason_exact(result: AgentContext, expected: str):
    assert result.reason == expected, f"Expected reason {expected!r}, got {result.reason!r}"


@then(parsers.parse('the reason contains "{fragment}"'))
def reason_contains(result: AgentContext, fragment: str):
    assert result.reason is not None, "Expected a reason but got None"
    assert fragment in result.reason, f"Expected {fragment!r} in reason {result.reason!r}"
