Feature: Run Queue and Wait Management
  As a DevOps engineer
  I want to manage the execution queue and wait for completions
  So I can reliably automate infrastructure changes in CI/CD pipelines

  Background:
    Given a terraform cloud organization is accessible
    And a workspace "my-app-dev" is ready for operations

  Scenario: Waiting for a run to complete
    When I trigger a new plan for "my-app-dev" with --wait
    Then the command should block until the run is "planned"
    And the command should exit with code 0

  Scenario: Waiting for a busy queue
    Given the workspace "my-app-dev" has an active run "run-busy"
    When I trigger a new plan for "my-app-dev" with --wait-queue
    Then it should first wait for "run-busy" to complete
    And the command should exit with code 0
    And then it should trigger the new run

  Scenario: Clearing the queue before triggering
    Given the workspace "my-app-dev" has several pending runs
    When I trigger a new plan for "my-app-dev" with --discard-older
    Then all existing non-terminal runs should be discarded
    And the command should exit with code 0
    And then it should trigger the new run

  Scenario: Exiting with success when paused for approval
    Given the run reaches "planned" status
    And auto-apply is disabled
    When I trigger a new plan for "my-app-dev" with --wait
    Then the command should exit with code 0
    And the output should indicate it is paused for approval
