Feature: Session-Gated Deletions for Agents
  As a DevOps engineer using AI coding agents
  I want destructive operations to require an explicit human session grant in automated contexts
  So that autonomous agents cannot accidentally destroy infrastructure resources in Terraform Cloud

  Scenario: Interactive human terminal allows workspace deletion with force flag
    Given the current execution context is an interactive human terminal
    And a workspace named "dev-sandbox" exists in the organization
    When I run "tfc workspace delete dev-sandbox --force"
    Then the command succeeds
    And the workspace "dev-sandbox" is deleted via the API

  Scenario: Agent session without grant is refused when attempting workspace deletion
    Given the current execution context is an automated agent session
    And no deletion grants are configured
    And a workspace named "prod-cluster" exists in the organization
    When I run "tfc workspace delete prod-cluster --force"
    Then the command exits with refusal code 1
    And no API deletion request was made
    And stderr indicates deletion of "workspace" is gated in agent sessions
    And the error hints suggest running with "tfc harness exec --allow-delete=workspace"

  Scenario: Agent session with matching grant successfully executes workspace deletion
    Given the current execution context is an automated agent session
    And the active session grants deletion for "workspace"
    And a workspace named "temp-scratch" exists in the organization
    When I run "tfc workspace delete temp-scratch --force"
    Then the command succeeds
    And the workspace "temp-scratch" is deleted via the API

  Scenario: Agent session with wildcard grant allows deleting variables
    Given the current execution context is an automated agent session
    And the active session grants deletion for "all"
    And a variable "DB_PASSWORD" exists on workspace "dev-sandbox"
    When I run "tfc workspace var remove dev-sandbox DB_PASSWORD --yes"
    Then the command succeeds
    And the variable "DB_PASSWORD" is removed via the API

  Scenario: Agent session without grant is refused on raw HTTP DELETE
    Given the current execution context is an automated agent session
    And no deletion grants are configured
    When I run "tfc api -X DELETE /workspaces/ws-123"
    Then the command exits with refusal code 1
    And no API deletion request was made
    And stderr indicates deletion of "api" is gated in agent sessions

  Scenario: Harness exec launches command with requested deletion grant
    Given the current execution context is an automated agent session
    When I run "tfc harness exec --allow-delete=workspace -- tfc workspace delete temp-scratch --force"
    Then the child process runs with "workspace" deletion granted
