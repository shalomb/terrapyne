Feature: Project Context Resolution
  As a DevOps engineer
  I want project commands to automatically detect the current project
  So that I don't have to specify the project name when working in a workspace

  Scenario: Show project details using workspace context
    Given I am in a directory for workspace "app-dev"
    And workspace "app-dev" belongs to project "Project-X"
    When I run "tfc project show"
    Then the command should succeed
    And the output should show details for project "Project-X"

  Scenario: List project teams using workspace context
    Given I am in a directory for workspace "app-dev"
    And workspace "app-dev" belongs to project "Project-X"
    When I run "tfc project teams"
    Then the command should succeed
    And the output should show team access for project "Project-X"

  Scenario: Workspace show reports the project name
    Given I am in a directory for workspace "app-dev"
    And workspace "app-dev" belongs to project "Project-X"
    When I run "tfc workspace show"
    Then the command should succeed
    And the output should show project "Project-X" in workspace details
