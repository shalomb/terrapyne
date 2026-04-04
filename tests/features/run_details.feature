Feature: Run Details and Diagnostics
  As a DevOps engineer
  I want to inspect the details of a specific execution
  So I can understand the exact impact and outcomes of a change

  Background:
    Given a terraform cloud organization is accessible
    And an existing run "run-abc123" in workspace "my-app-dev"

  Scenario: Inspecting a successful execution
    When I examine the details of run "run-abc123"
    Then the current status of the execution should be shown
    And the user message for the run should be visible
    And the precise time of execution should be indicated
    And I should see how many resources were affected

  Scenario: Monitoring an in-progress execution
    Given the run "run-abc123" is currently "pending"
    When I examine the run details
    Then the status should be identified as "pending"
    And there should be a clear indication that work is ongoing

  Scenario: Analyzing a failed execution
    Given the run "run-failed123" encountered an "error"
    When I examine the details of the failed run
    Then the status should be identified as "errored"
    And the primary error message should be presented

  Scenario: Reviewing the plan impact of an execution
    Given the execution "run-abc123" has a generated plan
    When I review the plan for this execution
    Then the proposed infrastructure changes should be summarized
    And I should see specific counts for additions, modifications, and deletions

  Scenario: Accessing execution logs
    Given the execution "run-abc123" has available logs
    When I retrieve the logs for this execution
    Then the output should contain the formatted terminal logs
    And the logs should be presented in a readable format

  Scenario: Handling requests for missing execution data
    Given an execution ID "run-nonexistent" that does not exist
    When I attempt to examine its details
    Then I should be notified that the record was not found
    And the request should not proceed
