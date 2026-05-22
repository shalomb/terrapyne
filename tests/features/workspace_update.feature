Feature: Workspace Update
  As a Terraform Cloud user
  I want to update workspace configurations
  So that I can change execution modes, Terraform versions, or move workspaces to other projects without the UI

  Scenario: Successfully update workspace execution mode and Terraform version
    Given the TFC API accepts workspace updates
    When I request to update the workspace "my-app-dev" with version "1.4.0" and execution mode "local"
    Then the command succeeds
    And the output shows the workspace was successfully updated

  Scenario: Workspace update fails due to invalid project name
    Given the TFC API rejects the project lookup
    When I request to update the workspace "my-app-dev" to project "nonexistent-project"
    Then the command fails
    And the error output indicates the project could not be found
