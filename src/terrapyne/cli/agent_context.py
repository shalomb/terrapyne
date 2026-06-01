"""Agent context detection for adaptive CLI output.

Terrapyne detects whether it is being invoked by a human at a terminal or by
an automated agent/pipeline and adjusts its default output format accordingly.

Per ADR-006, TTY state is the primary and authoritative signal:

  If stdout is not a tty → JSON output (program is consuming stdout)
  If stdout is a tty     → human-readable output (human is watching)

Detection is tiered, with the first match winning:

  Tier 1 — Explicit declaration (unconditional; covers PTY-allocating agents)
    TERRAPYNE_OUTPUT=json, NO_COLOR,
    TF_IN_AUTOMATION, CI, GITHUB_ACTIONS, ...

  Tier 2 — Known agent harness (cooperative agents that self-identify)
    CLAUDECODE, GEMINI_CLI, ANTIGRAVITY_AGENT, PI_CODING_AGENT,
    COPILOT_CLI, AWS_EXECUTION_ENV=AmazonQ*
    (belt-and-suspenders for agents that allocate a PTY)

  Tier 3 — TTY inference (primary signal; catches all agents and human pipes)
    not sys.stdout.isatty()

The Tier 2 whitelist is not extended. Any agent not in Tier 1/2 is caught
by Tier 3. See ADR-006 for the full rationale.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

# Tier 1: CI/automation vars that are explicit contracts
_CI_VARS: tuple[str, ...] = (
    "TF_IN_AUTOMATION",
    "CI",
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
)

# Tier 2: Known agent harnesses that self-identify via env var
_AGENT_VARS: tuple[str, ...] = (
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "GEMINI_CLI",
    "ANTIGRAVITY_AGENT",
    "PI_CODING_AGENT",
    "COPILOT_CLI",
    "COPILOT_AGENT_SESSION_ID",
)


@dataclass(frozen=True)
class AgentContext:
    is_agent: bool
    reason: str | None  # human-readable explanation for --debug output

    def __bool__(self) -> bool:
        return self.is_agent


def detect(env: dict[str, str] | None = None, stdout_isatty: bool | None = None) -> AgentContext:
    """Detect whether the current invocation is from an agent or automation.

    Args:
        env: Environment mapping (defaults to os.environ). Injected for testing.
        stdout_isatty: Override for sys.stdout.isatty() result. Injected for testing.

    Returns:
        AgentContext with is_agent flag and the reason it was set.
    """
    if env is None:
        env = dict(os.environ)
    if stdout_isatty is None:
        stdout_isatty = sys.stdout.isatty()

    # Tier 1a: explicit opt-in
    if env.get("TERRAPYNE_OUTPUT", "").lower() == "json":
        return AgentContext(is_agent=True, reason="TERRAPYNE_OUTPUT=json")

    # Tier 1b: NO_COLOR convention (signals non-interactive; honour it)
    if "NO_COLOR" in env:
        return AgentContext(is_agent=True, reason="NO_COLOR is set")

    # Tier 1c: CI / automation vars
    for var in _CI_VARS:
        if env.get(var):
            return AgentContext(is_agent=True, reason=f"{var}={env[var]!r}")

    # Tier 2: known agent harness self-identification
    for var in _AGENT_VARS:
        if env.get(var):
            return AgentContext(is_agent=True, reason=f"{var}={env[var]!r}")

    # AWS_EXECUTION_ENV is a value-prefix match (e.g. "AmazonQ-For-CLI ...")
    aws_env = env.get("AWS_EXECUTION_ENV", "")
    if aws_env.startswith("AmazonQ"):
        return AgentContext(is_agent=True, reason=f"AWS_EXECUTION_ENV={aws_env!r}")

    # Tier 3: stdout is a pipe/redirect — catches unknown agents and human pipes alike
    if not stdout_isatty:
        return AgentContext(is_agent=True, reason="stdout is not a tty")

    return AgentContext(is_agent=False, reason=None)
