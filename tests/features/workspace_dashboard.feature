Feature: Workspace Activity Dashboard
  As a DevOps engineer
  I want to see a health and activity summary when I inspect a workspace
  So that I can assess its state and recent activity without opening the GUI

  Scenario: Workspace with recent successful run shows healthy status
    Given a workspace with a recently applied run
    When I show the workspace details
    Then I should see the workspace health snapshot
    And I should see the latest run information
    And I should see the active run count

  Scenario: Workspace with no run history shows unknown health
    Given a workspace with no runs
    When I show the workspace details
    Then I should see the workspace health snapshot
    And I should see unknown health status
    And I should see zero active runs

  Scenario: Workspace shows commit metadata from VCS
    Given a workspace with a run linked to a VCS repository
    When I show the workspace details
    Then I should see the latest commit SHA
    And I should see the commit author
    And I should see the commit message

  Scenario: Workspace shows queued runs in activity snapshot
    Given a workspace with multiple active runs
    When I show the workspace details
    Then I should see the count of active runs
    And I should see at least one run in active state

  Scenario: JSON output includes workspace snapshot data
    Given a workspace with run activity
    When I request workspace details in JSON format
    Then I should receive JSON output
    And I should see snapshot section with latest run info
    And I should see active runs count in the snapshot
