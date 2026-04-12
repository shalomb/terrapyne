Feature: Infrastructure Change Lifecycle
  As a DevOps engineer
  I want to trigger and control infrastructure executions
  So I can safely deploy and manage my cloud environment

  Background:
    Given a terraform cloud organization is accessible
    And a workspace "my-app-dev" is ready for operations

  Scenario: Triggering a plan-only infrastructure change
    When I trigger a new infrastructure plan for "my-app-dev"
    Then a new execution should be initiated
    And its initial status should be "pending"
    And I should receive the new execution ID
    And it should only propose changes without applying them

  Scenario: Triggering a destruction of environment
    When I trigger a total destruction of "my-app-dev"
    Then I should be required to confirm this destructive action
    And once confirmed, a destruction execution should be initiated

  Scenario: Applying a prepared change
    Given an execution "run-abc123" is awaiting confirmation
    When I authorize the execution to proceed
    Then the status should transition to "applying"
    And the infrastructure changes should be executed

  Scenario: Cancelling an unintended change
    Given an execution "run-pending123" is in a "pending" state
    When I discard the execution
    Then the execution should be halted
    And its final status should be "discarded"

  Scenario: Triggering a change with a descriptive message
    When I trigger a plan for "my-app-dev" with the message "Release v2.0"
    Then the new execution should be labeled with "Release v2.0"
    And I should see the execution tracking ID

  Scenario: Triggering a change with TFC debug mode enabled
    When I trigger a plan for "my-app-dev" with the "--debug-run" flag
    Then the new execution should have "debugging-mode" enabled

  Scenario: Triggering a change targeted at specific components
    When I trigger a plan for "my-app-dev" targeting:
      | aws_instance.web |
      | aws_instance.api |
    Then the execution should only evaluate the specified components

  Scenario: Real-time monitoring of an execution
    Given an infrastructure change "run-123" is currently in progress
    When I start monitoring the progress of "run-123"
    Then I should see continuous status updates
    And I should eventually see the final completion summary

  Scenario: Waiting in queue when workspace is blocked
    Given a workspace "my-app-dev" is blocked by an earlier run
    When I trigger a plan for "my-app-dev" with the "--wait" flag
    Then I should be notified of the blocking run
    And I should remain in the queue until it clears

  Scenario: Automatically clearing a blocked queue
    Given a workspace "my-app-dev" is blocked by an earlier run
    When I trigger a plan for "my-app-dev" with the "--discard-older" flag
    Then the earlier blocking run should be automatically discarded
    And my new execution should proceed to planning

  Scenario: Triggering a change with automatic application
    When I trigger a plan for "my-app-dev" with the "--auto-apply" flag
    Then the new execution should be configured for "auto-apply"
    And once the plan succeeds, it should proceed to "applying" automatically

  Scenario: Triggering a refresh-only operation
    When I trigger a plan for "my-app-dev" with the "--refresh-only" flag
    Then the new execution should be a "refresh-only" run
    And it should only identify drift without proposing configuration changes

  Scenario: Streaming plan logs as they arrive
    Given an execution "run-log1" is planning infrastructure changes
    When I request to stream logs for "run-log1"
    Then I should see plan logs appear in real time
    And each log line should arrive as it becomes available
    And streaming should stop when the plan phase completes

  Scenario: Streaming apply logs after plan completion
    Given an execution "run-log2" has completed planning and started applying
    When I request to stream logs for "run-log2"
    Then I should see plan logs from the completed phase
    And then see apply logs as they arrive
    And streaming should continue until the apply finishes

  Scenario: No logs available when run is pending
    Given an execution "run-log3" is pending with no plan started
    When I request to stream logs for "run-log3"
    Then no logs should be returned
    And polling should continue waiting for the plan to start
    And streaming should stop when the run reaches a terminal state

  Scenario: Handling transient errors during log streaming
    Given an execution "run-log4" is planning infrastructure
    And log API calls will intermittently fail
    When I request to stream logs for "run-log4"
    Then failed log fetches should be retried automatically
    And successful log lines should still be yielded
    And streaming should complete despite transient failures

  Scenario: Stopping log stream when run reaches terminal state
    Given an execution "run-log5" is in progress
    When I request to stream logs for "run-log5"
    And the execution reaches a terminal state
    Then no further API calls should be made
    And streaming should exit cleanly
