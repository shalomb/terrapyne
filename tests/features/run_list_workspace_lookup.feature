Feature: Run List Workspace Name Lookup
  As a DevOps engineer
  I want "tfc run list" to reliably resolve workspace names
  So that workspaces with hyphens and digits are found correctly

  Background:
    Given a terraform cloud organization is accessible

  Scenario: List runs for a workspace with a simple name
    Given workspace "my-app-dev" exists in the organization
    When I run "tfc run list --workspace my-app-dev"
    Then the workspace should be resolved by name "my-app-dev"
    And runs should be fetched using the workspace ID
    And exit code should be 0

  Scenario: List runs for a workspace name containing digits and hyphens
    Given workspace "tec-dce-inn-dev-93400-shalombhooshi" exists in the organization
    When I run "tfc run list --workspace tec-dce-inn-dev-93400-shalombhooshi"
    Then the workspace should be resolved by name "tec-dce-inn-dev-93400-shalombhooshi"
    And runs should be fetched using the workspace ID
    And exit code should be 0

  Scenario: Workspace lookup uses direct endpoint not fuzzy search
    Given workspace "tec-dce-inn-dev-93400-shalombhooshi" exists in the organization
    When the workspace API fetches the workspace by name
    Then it should use the direct endpoint "/organizations/{org}/workspaces/{name}"
    And it should NOT use search[name] which returns partial matches

  Scenario: Run list fails gracefully when workspace does not exist
    Given workspace "non-existent-ws" does not exist in the organization
    When I run "tfc run list --workspace non-existent-ws"
    Then I should see an error message containing "not found"
    And exit code should be 1
