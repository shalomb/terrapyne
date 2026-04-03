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

  # Workspace Clone Feature Scenarios

  Scenario: Clone workspace with basic settings only
    Given I have workspace "prod-app" in organization "test-org"
    When I clone workspace "prod-app" to "staging-app"
    Then new workspace "staging-app" should be created
    And workspace "staging-app" should have same terraform version as "prod-app"
    And workspace "staging-app" should have same execution mode as "prod-app"
    And workspace "staging-app" should have same auto-apply setting as "prod-app"
    And exit code should be 0

  Scenario: Clone workspace with variables
    Given I have workspace "prod-app" with 3 variables
    And variables include both terraform and environment types
    And some variables are marked as sensitive
    When I clone workspace "prod-app" to "staging-app" with --with-variables
    Then new workspace "staging-app" should be created
    And workspace "staging-app" should have 3 variables
    And all variables should preserve their category (terraform/env)
    And all variables should preserve their sensitive flags
    And output should show "Variables cloned: 3"
    And exit code should be 0

  Scenario: Clone workspace with VCS configuration
    Given I have workspace "prod-app" with VCS repository configured
    And VCS repository is "github.com/acme/terraform" on branch "main"
    When I clone workspace "prod-app" to "staging-app" with --with-vcs
    Then new workspace "staging-app" should be created
    And workspace "staging-app" should have same VCS configuration
    And VCS repository should be "github.com/acme/terraform"
    And VCS branch should be "main"
    And output should show VCS configuration details
    And exit code should be 0

  Scenario: Clone workspace with variables and VCS
    Given I have workspace "prod-app" with variables and VCS configured
    When I clone workspace "prod-app" to "staging-app" with --with-variables --with-vcs
    Then new workspace "staging-app" should be created
    And workspace "staging-app" should have same variables
    And workspace "staging-app" should have same VCS configuration
    And output should show both variable and VCS counts
    And exit code should be 0

  Scenario: Clone fails when source workspace not found
    Given workspace "non-existent" does not exist in "test-org"
    When I try to clone "non-existent" to "target-app"
    Then I should see error message containing "not found"
    And I should see error message containing "non-existent"
    And workspace "target-app" should not be created
    And exit code should be 1

  Scenario: Clone fails when target workspace already exists
    Given I have workspace "existing-target" in "test-org"
    And I have workspace "prod-app" in "test-org"
    When I try to clone "prod-app" to "existing-target"
    Then I should see error message containing "already exists"
    And I should see suggestion to use "--force"
    And workspace "existing-target" should not be modified
    And exit code should be 1

  Scenario: Clone with force flag overwrites existing target
    Given I have workspace "existing-target" in "test-org"
    And I have workspace "prod-app" with terraform version "1.5.0"
    When I clone "prod-app" to "existing-target" with --force
    Then workspace "existing-target" should be updated
    And workspace "existing-target" should have terraform version from "prod-app"
    And clone operation should succeed
    And exit code should be 0

  Scenario: Clone shows detailed progress and results
    Given I have workspace "prod-app" with 2 variables and VCS configured
    When I clone "prod-app" to "staging-app" with --with-variables --with-vcs
    Then output should show "Cloning workspace: prod-app → staging-app"
    And output should show success message with checkmark
    And output should show target workspace ID
    And output should show "Variables cloned: 2"
    And output should show variable breakdown (terraform vs env)
    And output should show "VCS configured:" with repository details
    And exit code should be 0

  Scenario: Clone without variables or VCS copies settings only
    Given I have workspace "prod-app" with variables and VCS
    When I clone "prod-app" to "staging-app" without any optional flags
    Then workspace "staging-app" should be created with prod-app settings
    And workspace "staging-app" should NOT have prod-app variables
    And workspace "staging-app" should NOT have prod-app VCS configuration
    And output should show success message
    And exit code should be 0
