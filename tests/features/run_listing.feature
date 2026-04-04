Feature: Run Listing and Monitoring
  As a DevOps engineer
  I want to review recent execution history across my workspaces
  So I can monitor infrastructure stability and progress

  Background:
    Given a terraform cloud organization is accessible
    And I am targeting the "my-app-dev" workspace

  Scenario: Reviewing recent runs for a workspace
    Given the workspace has a history of recent executions
    When I request a list of recent runs
    Then I should see a summary of recent operations
    And the list should identify each run by its unique ID
    And the current status of each run should be visible
    And the execution time should be displayed for each entry

  Scenario: Filtering runs by execution status
    Given the workspace has runs with various statuses including "applied"
    When I filter the run history for "applied" operations
    Then the resulting list should only contain "applied" runs
    And the total count should reflect the filter criteria

  Scenario: Limiting the number of displayed runs
    Given the workspace has a large number of past runs
    When I request only the "5" most recent entries
    Then I should see no more than 5 results
    And the output should indicate that more results are available

  Scenario: Navigating through paginated run history
    Given there are "150" runs in the execution history
    When I view the run list
    Then I should see the most recent page of results
    And the total number of available entries should be indicated
    And I should see how many entries are currently being displayed

  Scenario: Handling ambiguous workspace context for run history
    Given I have not specified a target workspace
    When I attempt to list recent runs
    Then I should receive guidance on how to specify a workspace
    And the request should not proceed
