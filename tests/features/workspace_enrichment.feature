Feature: Workspace Dashboard Snapshot
  As a DevOps engineer
  I want a comprehensive snapshot of my workspace at a single glance
  So that I can quickly assess its health and activity without the GUI

  Scenario: Show workspace dashboard with active runs and VCS info
    Given a Terraform Cloud workspace "app-prod" exists in project "Core-Infra"
    And the workspace "app-prod" has 3 runs currently queued or in progress
    And the latest run for "app-prod" was "applied" successfully
    And the workspace "app-prod" is linked to "org/repo" branch "main"
    And the latest commit was "a1b2c3d" by "Alice" - "feat: initial commit"
    When I run "tfc workspace show app-prod"
    Then the command should succeed
    And the output should show "Project"
    And the output should show "Core-Infra"
    And the output should show "Health"
    And the output should show "🟢 Healthy (last run applied)"
    And the output should show "Queued Runs"
    And the output should show "3"
    And the output should show "Latest Commit"
    And the output should show "a1b2c3d (Alice)"
    And the output should show "Commit Message"
    And the output should show "feat: initial commit"
