Feature: Adaptive CLI output based on agent context

  Terrapyne automatically selects the right output format based on whether
  it is invoked by a human at a terminal or an agent/pipeline. Agents get
  JSON by default; humans get rich tables. No flags required.

  Rule: Agents receive JSON output without passing --format json

    Scenario: workspace list defaults to JSON when CLAUDECODE is set
      Given the CLI is running under a Claude Code agent context
      And workspaces exist in the organization
      When I run "workspace list" without a format flag
      Then the output is valid JSON
      And each workspace has an "id" and "name"

    Scenario: workspace show defaults to JSON when CLAUDECODE is set
      Given the CLI is running under a Claude Code agent context
      And workspace "my-app-dev" exists
      When I run "workspace show" without a format flag
      Then the output is valid JSON
      And the result has key "id"

    Scenario: run list defaults to JSON when running in CI
      Given the CLI is running in a CI pipeline
      And a workspace with runs exists
      When I run "run list" without a format flag
      Then the output is valid JSON
      And each run has an "id" and "status"

    Scenario: team list defaults to JSON when stdout is a pipe
      Given the CLI is running with stdout piped
      And teams exist in the organization
      When I run "team list" without a format flag
      Then the output is valid JSON
      And each team has an "id" and "name"

  Rule: Humans receive rich table output at an interactive terminal

    Scenario: workspace list renders a table for human users
      Given the CLI is running as a human in an interactive terminal
      And workspaces exist in the organization
      When I run "workspace list" without a format flag
      Then the output is not JSON
      And the output contains the workspace name

  Rule: Explicit --format flag overrides agent context

    Scenario: human can request JSON with --format json
      Given the CLI is running as a human in an interactive terminal
      And workspaces exist in the organization
      When I run "workspace list" with "--format json"
      Then the output is valid JSON

    Scenario: agent can request table with --format table
      Given the CLI is running under a Claude Code agent context
      And workspaces exist in the organization
      When I run "workspace list" with "--format table"
      Then the output is not JSON
      And the output contains the workspace name

  Rule: Debug mode reports why agent context was detected

    Scenario: --debug prints the agent context reason
      Given the CLI is running under a Claude Code agent context
      And workspaces exist in the organization
      When I run "workspace list" with "--debug"
      Then the output contains "Agent context detected"
      And the output contains "CLAUDECODE"
