Feature: Workspace Variable Subgroup
  As a Terraform Cloud user
  I want to manage workspace variables through a unified subcommand group
  So that variable operations are consistently grouped under "workspace var"

  Scenario: List variables for a workspace
    Given workspace "my-app-dev" has variables configured
    When I list variables for workspace "my-app-dev"
    Then I should see the variable listing
    And exit code should be 0

  Scenario: Set a new variable in a workspace
    Given workspace "my-app-dev" exists with no existing variables
    When I set variable "region" to "us-east-1" in workspace "my-app-dev"
    Then the variable should be created
    And output should confirm "Created variable: region"
    And exit code should be 0

  Scenario: Update an existing variable in a workspace
    Given workspace "my-app-dev" has variable "region" set to "us-west-2"
    When I set variable "region" to "eu-west-1" in workspace "my-app-dev"
    Then the variable should be updated
    And output should confirm "Updated variable: region"
    And exit code should be 0

  Scenario: Remove a variable from a workspace with force flag
    Given workspace "my-app-dev" has variable "old-var" configured
    When I remove variable "old-var" from workspace "my-app-dev" with --force
    Then the variable should be deleted
    And output should confirm "Removed variable: old-var"
    And exit code should be 0

  Scenario: Remove a variable without interactive prompt using --yes flag
    Given workspace "my-app-dev" has variable "old-var" configured
    When I remove variable "old-var" from workspace "my-app-dev" with --yes
    Then the variable should be deleted
    And output should confirm "Removed variable: old-var"
    And exit code should be 0

  Scenario: Copy variables between workspaces
    Given workspace "prod-app" has 2 variables
    And workspace "staging-app" has no variables
    When I copy variables from "prod-app" to "staging-app"
    Then 2 variables should be created in "staging-app"
    And output should confirm variables were copied
    And exit code should be 0
