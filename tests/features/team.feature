Feature: Team Management
  As a TFC Administrator
  I want to manage teams and their memberships
  So I can control access to my organization's resources

  Background:
    Given a terraform cloud organization is accessible

  Scenario: List teams in organization
    Given the organization has teams "platform", "developers", "security"
    When I list all teams
    Then I should see "platform" in the list
    And I should see "developers" in the list
    And I should see "security" in the list

  Scenario: Create a new team
    When I create a team named "new-team" with "Manage workspaces" permission
    Then the team "new-team" should be created successfully
    And it should have the requested permissions

  Scenario: Delete a team
    Given a team "old-team" exists
    When I delete the team "old-team"
    Then the team should be removed from the organization

  Scenario: Manage team membership
    Given a team "devs" exists
    And a user "user-123" is a member of the organization
    When I add "user-123" to the "devs" team
    Then "user-123" should be listed as a member of "devs"
    When I remove "user-123" from the "devs" team
    Then "user-123" should no longer be a member of "devs"
