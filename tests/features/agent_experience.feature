Feature: Agent Experience (AX) — Eliminating glue logic
  As an AI coding agent orchestrating TFC workflows
  I want first-class CLI primitives for common patterns
  So I can avoid bash pipes, jq, and polling loops

  Background:
    Given a terraform cloud organization is accessible

  # AX1 — Universal ID Resolver
  Scenario: Resolve workspace ID without jq
    Given a workspace "my-app-dev" exists
    When I run "tfc workspace id my-app-dev"
    Then stdout is exactly "ws-abc123"
    And there is no extra formatting

  Scenario: Resolve project ID without jq
    Given a project "platform" exists with id "prj-xyz789"
    When I run "tfc project id platform"
    Then stdout is exactly "prj-xyz789"
    And there is no extra formatting

  Scenario: Resolving ID for a non-existent workspace exits non-zero
    When I resolve the id of a workspace that does not exist
    Then the exit code is 1
    And stderr contains "not found"

  # AX2 — Latest Run Lookups
  Scenario: Show logs for the latest run without knowing its ID
    Given a workspace "my-app-dev" has runs
    When I run "tfc run logs --workspace my-app-dev --latest"
    Then the logs for the most recent run are shown

  Scenario: Show run detail for the latest run without knowing its ID
    Given a workspace "my-app-dev" has a most recent run "run-latest-001"
    When I run "tfc run show --workspace my-app-dev --latest"
    Then the run detail for "run-latest-001" is shown

  # AX3 — Trigger and Wait (silent, no log streaming)
  Scenario: Trigger a run and wait silently for completion
    Given a workspace "my-app-dev" is ready for operations
    When I trigger a run for "my-app-dev" with "--wait"
    Then the command blocks until the run reaches a terminal state
    And no plan or apply logs are streamed
    And the command exits with code 0 on success

  Scenario: Trigger and wait exits non-zero when run errors
    Given a workspace "my-app-dev" is ready for operations
    When I trigger a run for "my-app-dev" with "--wait" and the run errors
    Then the command exits with code 1

  # AX4 — State Output Extraction
  Scenario: Extract a single state output value
    Given a workspace with output "vpc_id" = "vpc-0abc1234"
    When I run "tfc state output my-app-dev vpc_id"
    Then stdout is exactly "vpc-0abc1234"
    And there is no table formatting

  Scenario: Extracting a missing state output exits non-zero
    Given a workspace with no output named "missing_key"
    When I run "tfc state output my-app-dev missing_key"
    Then the exit code is 1
    And stderr contains "not found"

  # AX5 — JSON output for mutation commands
  Scenario: workspace create emits JSON with workspace ID
    When I create workspace "my-new-ws" with "--format json"
    Then stdout is valid JSON
    And the JSON contains field "id" matching "ws-*"
    And the JSON contains field "name" = "my-new-ws"

  Scenario: workspace clone emits JSON with new workspace ID
    Given a workspace "my-app-dev" exists
    When I clone "my-app-dev" to "my-app-staging" with "--format json"
    Then stdout is valid JSON
    And the JSON contains field "id" matching "ws-*"
    And the JSON contains field "name" = "my-app-staging"

  Scenario: run trigger emits JSON with run ID
    Given a workspace "my-app-dev" is ready for operations
    When I trigger a run for "my-app-dev" with "--format json"
    Then stdout is valid JSON
    And the JSON contains field "id" matching "run-*"
    And the JSON contains field "status"

  # AX6 — Idempotent create
  Scenario: workspace create with --ignore-exists succeeds when workspace already present
    Given a workspace "my-app-dev" already exists
    When I create workspace "my-app-dev" with "--ignore-exists"
    Then the command exits with code 0
    And the existing workspace is returned without creating a duplicate

  Scenario: workspace create without --ignore-exists fails when workspace exists
    Given a workspace "my-app-dev" already exists
    When I create workspace "my-app-dev" without "--ignore-exists"
    Then the command exits with code 1
    And stderr contains "already exists"
