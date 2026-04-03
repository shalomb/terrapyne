Feature: Workspace Operations
  As a DevOps engineer
  I want to manage Terraform Cloud workspaces
  So I can organize and control my infrastructure

  Scenario: List all workspaces in organization
    Given I have organization "test-org" set up
    When I list all workspaces
    Then I should see workspace list
    And the list should show workspace count

  Scenario: List workspaces with search filter
    Given I have organization "test-org" with workspaces
    When I search for workspaces matching "dev"
    Then I should only see workspaces matching "dev"
    And the count should reflect filtered results

  Scenario: Show workspace details
    Given I have workspace "my-app-dev" in organization "test-org"
    When I show workspace details for "my-app-dev"
    Then I should see workspace properties
    And I should see workspace ID
    And I should see terraform version
    And I should see execution mode

  Scenario: Show workspace with variables
    Given I have workspace "my-app-dev" with variables
    When I show workspace "my-app-dev"
    Then I should see variables section
    And variables table should display
    And sensitive variables should be masked

  Scenario: Show workspace with VCS configuration
    Given I have workspace "my-app-dev" with VCS connection
    When I show workspace "my-app-dev"
    Then I should see VCS configuration
    And I should see repository identifier
    And I should see branch name

  Scenario: Show VCS configuration only
    Given I have workspace "my-app-dev" with VCS configured
    When I show VCS config for workspace "my-app-dev"
    Then I should see repository information
    And I should see branch information
    And I should see auto-apply setting

  Scenario: Handle workspace without VCS
    Given I have workspace "unconnected-ws" without VCS
    When I show VCS config for "unconnected-ws"
    Then I should see message "no VCS connection"
    And exit code should be 0

  Scenario: Open workspace in browser
    Given I have workspace "my-app-dev" in "test-org"
    When I open workspace in browser
    Then browser should open with correct URL
    And URL should contain organization name
    And URL should contain workspace name

  Scenario: Open workspace with specific page
    Given I have workspace "my-app-dev"
    When I open workspace runs page
    Then URL should contain "/runs" endpoint

  Scenario: Handle missing workspace
    Given workspace "non-existent" does not exist
    When I try to show workspace "non-existent"
    Then I should see error message "not found"
    And exit code should be 1

  Scenario: Handle missing organization
    Given no organization is specified
    When I try to list workspaces
    Then I should see error message "No organization specified"
    And error message should mention "--organization"
    And exit code should be 1

  Scenario: Auto-detect organization from context
    Given I am in terraform directory with context
    When I list workspaces without specifying organization
    Then I should list workspaces
    And should use organization from context
    And should not error about missing organization

  Scenario: Override organization context
    Given I am in terraform directory with context
    When I list workspaces with --organization "other-org"
    Then I should list workspaces from "other-org"
    And should ignore context organization
