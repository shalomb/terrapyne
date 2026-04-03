Feature: VCS Operations
  As a DevOps engineer
  I want to manage VCS connections for Terraform Cloud workspaces
  So I can control which repository branches run terraform

  Scenario: Show VCS configuration for workspace
    Given I have workspace "my-app-dev" with VCS connected
    When I show VCS configuration
    Then I should see repository identifier
    And I should see repository branch
    And I should see working directory if set
    And I should see repository URL
    And I should see auto-apply setting

  Scenario: Show VCS without working directory
    Given I have workspace with VCS at root
    When I show VCS configuration
    Then I should see repository information
    And working directory should not be displayed
    And display should be clean and focused

  Scenario: Handle workspace without VCS
    Given I have workspace without VCS connection
    When I show VCS configuration
    Then I should see message "no VCS connection"
    And exit code should be 0
    And should not show repository details

  Scenario: Update workspace VCS branch
    Given I have workspace "my-app-dev" with VCS connected
    When I update VCS branch to "main"
    Then branch should be updated to "main"
    And configuration should reflect change

  Scenario: Update VCS branch with confirmation
    Given I have workspace with VCS configured
    When I update VCS branch with confirmation required
    And I confirm the change
    Then branch should be updated
    And update should be successful

  Scenario: Update VCS branch with auto-approve
    Given I have workspace with VCS configured
    When I update VCS branch with --auto-approve flag
    Then branch should be updated immediately
    And no confirmation should be requested

  Scenario: Handle VCS update without OAuth token
    Given I have workspace with VCS
    And TFC_VCS_OAUTH_TOKEN is not set
    When I try to update VCS branch
    Then I should see error about missing OAuth token
    And update should fail
    And exit code should be 1

  Scenario: List available VCS repositories
    Given I have VCS OAuth token configured
    When I list available repositories
    Then I should see repository list
    And each repository should show identifier
    And each repository should show branch list

  Scenario: Filter repositories by identifier
    Given I have multiple repositories available
    When I list repositories matching "myorg/*"
    Then I should only see matching repositories

  Scenario: Handle missing workspace context
    Given no workspace is specified
    When I try to show VCS configuration
    Then I should see error about missing workspace
    And error should mention "--workspace"
    And exit code should be 1

  Scenario: Handle missing organization context
    Given no organization is specified
    When I try to show VCS configuration
    Then I should see error about missing organization
    And exit code should be 1

  Scenario: VCS configuration with special characters
    Given I have workspace with VCS containing special characters in branch
    When I show VCS configuration
    Then special characters should be displayed correctly
    And branch name should be preserved exactly
