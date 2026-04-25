Feature: State Version Management
  As a DevOps engineer
  I want to inspect and retrieve terraform state versions
  So I can troubleshoot infrastructure issues and audit changes

  Background:
    Given a terraform cloud organization is accessible
    And a workspace "my-infra" is ready for operations

  Scenario: Pull current state as raw JSON
    Given the workspace has a current state version with ID "sv-123"
    And the state file contains "aws_instance.web"
    When I pull the current state
    Then the output should be valid JSON
    And it should contain "aws_instance.web"

  Scenario: List state versions with relative time
    Given the workspace has state versions:
      | ID     | Created             | Serial |
      | sv-003 | 1 hour ago          | 3      |
      | sv-002 | 2 days ago          | 2      |
      | sv-001 | last month          | 1      |
    When I list state versions
    Then I should see 3 versions in the list
    And I should see relative times like "1h ago" or "2d ago"
