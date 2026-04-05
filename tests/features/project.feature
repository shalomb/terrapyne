Feature: Project Operations
  As a DevOps engineer
  I want to organize and manage Terraform Cloud projects
  So I can group related workspaces and control team access

  Scenario: List all projects in organization
    Given I have organization "test-org" with projects
    When I list all projects
    Then I should see project list
    And list should show project names
    And list should show workspace counts
    And list should show project IDs

  Scenario: List projects with workspace count
    Given I have projects with varying workspace counts
    When I list projects
    Then each project should show its workspace count
    And workspace count should reflect actual workspaces

  Scenario: Find projects by pattern
    Given I have projects matching pattern "app-*"
    When I find projects matching "app-*"
    Then I should only see projects matching pattern
    And results should be filtered correctly

  Scenario: Find projects with wildcard
    Given I have projects like "backend-prod", "backend-staging", "frontend-prod"
    When I find projects matching "*-prod"
    Then I should only see "backend-prod" and "frontend-prod"

  Scenario: Show project details
    Given I have project "my-infrastructure"
    When I show details for project "my-infrastructure"
    Then I should see project ID
    And I should see project description
    And I should see creation date
    And I should see workspace count
    And I should see team count

  Scenario: Show project with multiple workspaces
    Given I have project with 5 workspaces
    When I show project details
    Then I should see workspace list
    And workspace count should show "5"
    And all workspaces should be displayed

  Scenario: List teams with project access
    Given I have project "my-infrastructure" with team access
    When I list team access for project
    Then I should see team names
    And I should see access levels (admin, maintain, read)
    And I should see team IDs
    And I should see project permissions
    And I should see workspace creation permissions

  Scenario: Show team with admin access
    Given I have project with team having admin access
    When I list project teams
    Then team should be marked as "ADMIN"
    And should have delete permissions
    And should have manage teams permission

  Scenario: Show team with read-only access
    Given I have project with read-only team
    When I list project teams
    Then team should be marked as "READ"
    And should have no write permissions
    And should have no create workspace permission

  Scenario: Show team with custom access
    Given I have project with custom access team
    When I list project teams
    Then team should be marked as "CUSTOM"
    And should show specific permissions granted

  Scenario: Handle project not found
    Given project "non-existent-project" does not exist
    When I try to show project "non-existent-project"
    Then I should see error "not found"
    And exit code should be 1

  Scenario: Handle missing organization
    Given no organization is specified
    When I try to list projects
    Then I should see error "No organization specified"
    And error should mention how to specify organization
    And exit code should be 1

  Scenario: Project search with no results
    Given I have projects but none match pattern "xyz-*"
    When I find projects matching "xyz-*"
    Then I should see message "No projects found"
    And exit code should be 0

  Scenario: List projects with pagination
    Given I have organization with 100 projects
    When I list projects
    Then I should see pagination info
    And pagination should show total count
    And count should show "Showing: X of 100 projects"

  Scenario: Show project details using client.projects property
    Given a TFCClient with mocked projects property
    When I call project show command
    Then the command should succeed
    And client.workspaces property should be called, not WorkspaceAPI constructor

  Scenario: List teams using client.projects property
    Given a TFCClient with mocked projects property for teams
    When I call project teams command
    Then teams command should succeed
    And client.projects.list_team_access should be called, not ProjectAPI constructor

  Scenario: List projects using client.projects property
    Given a TFCClient with mocked projects property for list
    When I call project list command
    Then list command should succeed
    And client.projects.list should be called, not ProjectAPI constructor
