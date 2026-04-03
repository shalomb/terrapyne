Feature: Run Operations
  As a DevOps engineer
  I want to view and manage Terraform Cloud runs
  So I can monitor and control apply/destroy operations

  Scenario: List runs for workspace
    Given I have workspace "my-app-dev" with runs
    When I list runs for "my-app-dev"
    Then I should see run list
    And list should show run IDs
    And list should show run status
    And list should show created timestamps

  Scenario: List runs with status filter
    Given I have workspace "my-app-dev" with multiple run statuses
    When I list runs with status "applied"
    Then I should only see runs with status "applied"
    And count should reflect filtered results

  Scenario: List runs with limit
    Given I have workspace "my-app-dev" with many runs
    When I list runs with limit "5"
    Then I should see at most 5 runs
    And list should show "Showing: 5 of X runs"

  Scenario: Show run details
    Given I have run "run-abc123" in workspace
    When I show details for run "run-abc123"
    Then I should see run status
    And I should see run message
    And I should see run created timestamp
    And I should see resource counts

  Scenario: Show run with pending status
    Given I have run "run-abc123" with status "pending"
    When I show run "run-abc123"
    Then I should see status "pending"
    And I should see indication that run is in progress

  Scenario: Show run with error
    Given I have run "run-failed123" with status "errored"
    When I show run "run-failed123"
    Then I should see status "errored"
    And I should see error message

  Scenario: View run plan
    Given I have run "run-abc123" with plan output
    When I view plan for run "run-abc123"
    Then I should see plan output
    And I should see resource additions
    And I should see resource changes
    And I should see resource destructions

  Scenario: View run logs
    Given I have run "run-abc123" with logs
    When I view logs for run "run-abc123"
    Then I should see log output
    And logs should be formatted properly

  Scenario: Create run (apply)
    Given I have workspace "my-app-dev"
    When I create run with apply
    Then run should be created
    And run should have status "pending"
    And run ID should be returned

  Scenario: Create run (destroy)
    Given I have workspace "my-app-dev"
    When I create destroy run
    Then run should be created with destroy flag
    And status should be "pending"

  Scenario: Apply run
    Given I have run "run-abc123" ready for apply
    When I apply run "run-abc123"
    Then run should transition to "applying"
    And changes should be applied

  Scenario: Discard run
    Given I have run "run-pending123" in pending state
    When I discard run "run-pending123"
    Then run should be discarded
    And status should be "discarded"

  Scenario: Handle non-existent run
    Given run "run-nonexistent" does not exist
    When I try to show run "run-nonexistent"
    Then I should see error "not found"
    And exit code should be 1

  Scenario: Handle missing workspace context
    Given no workspace is specified
    When I try to list runs
    Then I should see error about missing workspace
    And error should mention "--workspace"
    And exit code should be 1

  Scenario: List runs with pagination
    Given I have workspace with 150 runs
    When I list runs
    Then I should see first page of runs
    And pagination info should show total count
    And pagination should indicate "Showing: X of 150"

  Scenario: List errored runs across a project
    Given project "platform" has workspaces with recent errored runs:
      | workspace     | run-id      | error-summary               | created-at           |
      | app-prod      | run-aaa111  | Error: insufficient perms   | 2026-03-25T08:00:00Z |
      | db-prod       | run-bbb222  | Error: resource timeout     | 2026-03-25T07:30:00Z |
    When I run "terrapyne run errors --project platform"
    Then I should see both errored runs in a table
    And the table should include workspace name, run ID, error summary, and time

  Scenario: No errored runs shows clean output
    Given no workspaces have errored runs in the last 7 days
    When I run "terrapyne run errors --project platform --days 7"
    Then I should see "✅ No errored runs found in project 'platform' in the last 7 day(s)."

  Scenario: Trigger a normal run
    Given workspace "my-app-dev" exists
    When I run "terrapyne run trigger my-app-dev --message 'Deploy v2.0'"
    Then a new run should be created with the specified message
    And I should see the run ID

  Scenario: Trigger a targeted run for specific resources
    When I run "terrapyne run trigger my-app-dev --target aws_instance.web --target aws_instance.api"
    Then the run payload should include target addresses:
      | aws_instance.web |
      | aws_instance.api |

  Scenario: Trigger a destroy run
    When I run "terrapyne run trigger my-app-dev --destroy"
    Then I should be prompted "This will destroy all resources in 'my-app-dev'. Continue?"

  Scenario: Watch an existing run
    Given run "run-123" is in progress
    When I run "terrapyne run watch run-123"
    Then I should see the run status polling
    And eventually the final run summary
