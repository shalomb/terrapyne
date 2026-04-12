Feature: Wait for run completion in CI/CD pipelines
  As a CI/CD pipeline engineer
  I want to wait for run completion and get proper exit codes
  So I can automate infrastructure deployments with immediate feedback

  Background:
    Given a terraform cloud organization is accessible
    And a workspace "my-app-dev" is ready for operations

  Scenario: --wait blocks until run succeeds and exits 0
    Given a triggered run that will reach "applied" status
    When I run tfc run trigger my-app-dev --wait
    Then the command streams log lines to stdout
    And the exit code is 0

  Scenario: --wait exits non-zero when run fails
    Given a triggered run that will reach "errored" status
    When I run tfc run trigger my-app-dev --wait
    Then the exit code is 1
    And stderr contains the error message

  Scenario: --wait exits non-zero when run is discarded
    Given a triggered run that will be "discarded"
    When I run tfc run trigger my-app-dev --wait
    Then the exit code is 1

  Scenario: run apply --wait streams apply logs
    Given a run in "planned" status with apply_id
    When I run tfc run apply <run-id> --wait
    Then apply log lines are streamed to stdout
    And the exit code reflects the run outcome
