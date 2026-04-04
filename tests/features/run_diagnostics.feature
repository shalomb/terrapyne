Feature: Multi-Workspace Execution Diagnostics
  As a DevOps engineer
  I want to identify systemic infrastructure failures across projects
  So I can resolve root causes affecting multiple environments

  Background:
    Given a terraform cloud organization is accessible
    And a project "platform" containing various environments

  Scenario: Identifying common execution errors across a project
    Given the project "platform" has recently encountered execution errors:
      | environment   | execution-id | error-description           |
      | app-prod      | run-aaa111   | Error: insufficient perms   |
      | db-prod       | run-bbb222   | Error: resource timeout     |
    When I analyze recent project-wide execution failures
    Then I should see a report of all failed executions
    And the report should include environment names, IDs, and error summaries

  Scenario: Confirming projects with healthy execution status
    Given no environments in project "platform" have failed in the last "7" days
    When I analyze execution failures for the last "7" days
    Then I should be notified that no project errors were found
