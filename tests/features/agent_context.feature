Feature: Agent context detection

  Terrapyne adapts its default output format based on whether it is invoked
  by a human at a terminal or by an automated agent or pipeline.

  The goal is zero configuration for agents: the right output format is chosen
  automatically, without agents having to pass --format json explicitly.

  The primary signal is TTY state: if stdout is not a tty, JSON output is
  implied. This means terrapyne works correctly with any agent — known or
  unknown — without maintaining a whitelist. Explicit env var overrides
  (Tier 1/2) are retained for agents that allocate a pseudo-TTY.

  See ADR-006 for the full rationale.

  Rule: Explicit declarations are honoured unconditionally

    Scenario: TERRAPYNE_OUTPUT=json forces agent mode
      Given the environment has "TERRAPYNE_OUTPUT" set to "json"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason is "TERRAPYNE_OUTPUT=json"

    Scenario: NO_COLOR signals a non-interactive consumer
      Given the environment has "NO_COLOR" set to "1"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "NO_COLOR"

    Scenario: TF_IN_AUTOMATION signals a Terraform automation context
      Given the environment has "TF_IN_AUTOMATION" set to "1"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "TF_IN_AUTOMATION"

    Scenario: CI signals a continuous integration pipeline
      Given the environment has "CI" set to "true"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "CI"

    Scenario Outline: Common CI platform variables are recognised
      Given the environment has "<var>" set to "1"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent

      Examples:
        | var                    |
        | GITHUB_ACTIONS         |
        | GITLAB_CI              |
        | JENKINS_URL            |
        | CIRCLECI               |
        | TRAVIS                 |
        | BUILDKITE              |
        | TEAMCITY_VERSION       |
        | BITBUCKET_BUILD_NUMBER |
        | DRONE                  |
        | SEMAPHORE              |

  Rule: Known agent harnesses are recognised by their self-identification vars

    Scenario: Claude Code is detected by CLAUDECODE
      Given the environment has "CLAUDECODE" set to "1"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "CLAUDECODE"

    Scenario: Gemini CLI is detected by GEMINI_CLI
      Given the environment has "GEMINI_CLI" set to "1"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "GEMINI_CLI"

    Scenario: Antigravity agent is detected by ANTIGRAVITY_AGENT
      Given the environment has "ANTIGRAVITY_AGENT" set to "1"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "ANTIGRAVITY_AGENT"

    Scenario: Pi coding agent is detected by PI_CODING_AGENT
      Given the environment has "PI_CODING_AGENT" set to "true"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "PI_CODING_AGENT"

    Scenario: GitHub Copilot is detected by COPILOT_CLI
      Given the environment has "COPILOT_CLI" set to "1"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "COPILOT_CLI"

    Scenario: Amazon Q / Kiro is detected by AWS_EXECUTION_ENV prefix
      Given the environment has "AWS_EXECUTION_ENV" set to "AmazonQ-For-CLI Version/1.27.2"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "AWS_EXECUTION_ENV"

    Scenario: AWS_EXECUTION_ENV for non-agent AWS services is not misclassified
      Given the environment has "AWS_EXECUTION_ENV" set to "AWS_ECS_EC2"
      And stdout is a tty
      When agent context is detected
      Then it is identified as a human

  Rule: TTY state is the primary signal — non-TTY stdout means JSON output

    Scenario: Stdout piped to another process signals non-interactive use
      Given the environment is clean
      And stdout is not a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "stdout is not a tty"

    Scenario: Unknown agent with no recognised env var is caught by TTY check
      Given the environment has "SOME_UNKNOWN_AGENT" set to "1"
      And stdout is not a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "stdout is not a tty"

    Scenario: Human piping output to grep gets JSON — program is consuming stdout
      Given the environment is clean
      And stdout is not a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "stdout is not a tty"

  Rule: A human at an interactive terminal is not misclassified

    Scenario: Interactive terminal with no agent signals is classified as human
      Given the environment is clean
      And stdout is a tty
      When agent context is detected
      Then it is identified as a human

    Scenario: CLAUDECODE inherited in a human shell does not misclassify when stdout is a tty
      Given the environment has "CLAUDECODE" set to "1"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "CLAUDECODE"

  Rule: Tier 1 declarations take precedence over all other signals

    Scenario: TERRAPYNE_OUTPUT=json overrides a clean environment with tty
      Given the environment has "TERRAPYNE_OUTPUT" set to "json"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason is "TERRAPYNE_OUTPUT=json"

    Scenario: TF_IN_AUTOMATION takes precedence over a missing agent var
      Given the environment has "TF_IN_AUTOMATION" set to "1"
      And the environment does not have "CLAUDECODE"
      And stdout is a tty
      When agent context is detected
      Then it is identified as an agent
      And the reason contains "TF_IN_AUTOMATION"
