Feature: Repoint a workspace's VCS repository
  As a DevOps engineer
  I want to repoint workspaces to a renamed GitHub repository
  So that workspaces stop depending on GitHub's redirect from the old name

  Scenario: Dry run shows the change and sends nothing
    Given workspace "my-app-dev" is connected to repository "myorg/old-name"
    When I run "tfc vcs set-repo my-app-dev myorg/new-name --dry-run"
    Then the output should show "myorg/old-name" and "myorg/new-name"
    And no change should be sent to Terraform Cloud
    And exit code should be 0

  Scenario: Repoint a workspace
    Given workspace "my-app-dev" is connected to repository "myorg/old-name"
    When I run "tfc vcs set-repo my-app-dev myorg/new-name"
    Then the workspace repository should be set to "myorg/new-name"
    And exit code should be 0

  Scenario: Reject a malformed repository identifier
    Given workspace "my-app-dev" is connected to repository "myorg/old-name"
    When I run "tfc vcs set-repo my-app-dev not-a-repo"
    Then I should see error message containing "owner/repo"
    And no change should be sent to Terraform Cloud
    And exit code should be 1

  Scenario: Workspace without VCS is refused
    Given workspace "no-vcs-ws" has no VCS repository connected
    When I run "tfc vcs set-repo no-vcs-ws myorg/new-name"
    Then I should see error message containing "no VCS"
    And exit code should be 1

  Scenario: Workspace already uses the repository
    Given workspace "my-app-dev" is connected to repository "myorg/new-name"
    When I run "tfc vcs set-repo my-app-dev myorg/new-name"
    Then the output should show "already" and "myorg/new-name"
    And no change should be sent to Terraform Cloud
    And exit code should be 0
