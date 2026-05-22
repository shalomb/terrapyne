Feature: Infrastructure Change Lifecycle
  As a DevOps engineer
  I want to trigger and control infrastructure executions
  So I can safely deploy and manage my cloud environment

  Background:
    Given a terraform cloud organization is accessible
    And a workspace "my-app-dev" is ready for operations

  Scenario: Triggering a standard infrastructure change
    When I trigger a new infrastructure plan for "my-app-dev"
    Then a new execution should be initiated
    And its initial status should be "pending"
    And I should receive the new execution ID

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

  Scenario: Triggering a change targeted at specific components
    When I trigger a plan for "my-app-dev" targeting:
      | aws_instance.web |
      | aws_instance.api |
    Then the execution should only evaluate the specified components

  Scenario: Triggering a run with TFC debugging mode
    When I trigger a plan for "my-app-dev" with debugging enabled
    Then the new execution should be initiated with TFC debugging mode active

  Scenario: Real-time monitoring of an execution
    Given an infrastructure change "run-123" is currently in progress
    When I start monitoring the progress of "run-123"
    Then I should see continuous status updates
    And I should eventually see the final completion summary

  Scenario: Stream logs progressively during monitoring
    Given an infrastructure change "run-log-123" with plan and apply logs
    When I follow the logs of "run-log-123"
    Then the plan logs should be streamed progressively
    And the apply logs should be streamed progressively
    And no duplicate log lines should be printed

  Scenario: Triggering a true speculative plan
    When I trigger a speculative plan for "my-app-dev"
    Then a speculative configuration version should be created
    And a run should be associated with that configuration version
    And the run should not be confirmable

  Scenario: Watching an externally triggered run and auto-applying after planning
    Given an externally triggered run "run-ext-123" has reached "planned" status
    When I watch "run-ext-123" with --auto-apply
    Then the run should be applied automatically
    And the command should wait for the apply to complete
    And the command should exit with code 0

  Scenario: Watching an externally triggered run without auto-apply pauses at approval
    Given an externally triggered run "run-ext-456" has reached "planned" status
    When I watch "run-ext-456" without --auto-apply
    Then the run should not be applied
    And the output should indicate the run requires manual approval
    And the command should exit with code 0

  Scenario: Watching an externally triggered run that errors during planning
    Given an externally triggered run "run-ext-789" has errored
    When I watch "run-ext-789" with --auto-apply
    Then the run should not be applied
    And the command should exit with code 1

  Scenario: Following an externally triggered run and auto-applying after planning
    Given an externally triggered run "run-ext-999" has reached "planned" status
    When I follow "run-ext-999" with --auto-apply
    Then the run should be applied automatically
    And the command should wait for the apply to complete
    And the command should exit with code 0

  Scenario: Following a run that fails before producing plan output shows archivist error text
    Given an externally triggered run "run-prefail-001" errored before generating plan logs
    And the plan archivist URL contains "Error: Invalid provider configuration"
    When I follow "run-prefail-001"
    Then the output should contain "Error: Invalid provider configuration"
    And the output should not show "Run failed before generating logs"
