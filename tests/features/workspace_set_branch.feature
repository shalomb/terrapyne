Feature: Workspace Set VCS Branch
  As a DevOps engineer
  I want to switch a workspace's VCS branch from the CLI
  So I can test speculative changes without using raw curl commands

  Scenario: Set VCS branch on a workspace with VCS configured
    Given workspace "my-app-dev" is in organization "test-org"
    And the workspace has a VCS repository connected on branch "main"
    When I run "tfc workspace set-branch my-app-dev feature/my-change --organization test-org"
    Then the API should PATCH vcs-repo.branch to "feature/my-change"
    And the output should show the updated branch "feature/my-change"
    And exit code should be 0

  Scenario: Set VCS branch on a workspace without VCS configured
    Given workspace "no-vcs-ws" is in organization "test-org"
    And the workspace has no VCS repository connected
    When I run "tfc workspace set-branch no-vcs-ws feature/new --organization test-org"
    Then I should see error message containing "no VCS"
    And exit code should be 1

  Scenario: Set VCS branch with organization from context
    Given workspace "my-app-dev" is in organization "test-org"
    And the workspace has a VCS repository connected on branch "main"
    When I run "tfc workspace set-branch my-app-dev hotfix/123" without --organization
    Then the API should PATCH vcs-repo.branch to "hotfix/123"
    And exit code should be 0

  Scenario: API method set_vcs_branch sends correct PATCH payload
    Given a WorkspaceAPI instance
    When I call set_vcs_branch("my-app-dev", "feature/test", organization="test-org")
    Then the client should PATCH "/organizations/test-org/workspaces/my-app-dev"
    And the payload should have vcs-repo.branch set to "feature/test"
