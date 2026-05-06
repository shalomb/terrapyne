Feature: Org-Wide Errored Workspace Discovery
  As a DevOps engineer
  I want to identify all errored workspaces across my entire organisation in one command
  So I can quickly triage infrastructure failures without knowing which project they belong to

  Background:
    Given a terraform cloud organization is accessible

  Scenario: Discovering errored workspaces org-wide with a single API call
    Given the organisation has workspaces with errored latest runs:
      | workspace                  | run-id     | created-at               |
      | APMS1234-DEV-eks-cluster   | run-aaa111 | 2026-04-30T10:00:00Z     |
      | APMS5678-PRD-rds-db        | run-bbb222 | 2026-04-29T14:30:00Z     |
    When I scan for errored workspaces across the entire organisation
    Then the workspace API is called with filter "current-run.status" equal to "errored"
    And the workspace API is called with include "latest-run"
    And I should see both errored workspaces in the output

  Scenario: Org-wide scan uses a single paginated request, not per-workspace iteration
    Given the organisation has "150" workspaces with errored latest runs spread across "30" projects
    When I scan for errored workspaces across the entire organisation
    Then the workspace list endpoint is called exactly once
    And no per-workspace run list calls are made

  Scenario: Org-wide scan with no errored workspaces
    Given all workspaces in the organisation have healthy latest runs
    When I scan for errored workspaces across the entire organisation
    Then I should be notified that no errored workspaces were found

  Scenario: Scoping scan to a project still works
    Given a project "platform" containing workspaces with errors
    When I scan for errored workspaces scoped to project "platform"
    Then the workspace API is called with filter "current-run.status" equal to "errored"
    And the results are limited to the "platform" project

  Scenario: Filtering by lookback window
    Given the organisation has errored workspaces, some with errors older than 7 days
    When I scan for errored workspaces in the last "7" days
    Then only workspaces whose latest run errored within the last 7 days are shown
    And workspaces with older errors are excluded
