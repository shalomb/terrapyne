Feature: Terraform Plan Summary and Diagnostic Extraction
  As a DevOps engineer using Terrapyne
  I want to extract high-level summaries and diagnostic details from terraform plans
  So I can quickly assess the health and impact of my infrastructure

  Background:
    Given a terraform environment is ready
    And a plan is available from a remote execution

  # ============================================================================
  # PLAN SUMMARY
  # ============================================================================

  Scenario: Extraction of comprehensive plan statistics
    Given the plan summary reports "Plan: 2 to add, 1 to change, 1 to destroy."
    When the plan is analyzed
    Then the change totals should be:
      | category | count |
      | add      | 2     |
      | change   | 1     |
      | destroy  | 1     |

  Scenario: Extraction of statistics including imports
    Given the plan summary reports "Plan: 2 to add, 1 to change, 1 to destroy, 5 to import."
    When the plan is analyzed
    Then the change totals should be:
      | category | count |
      | add      | 2     |
      | change   | 1     |
      | destroy  | 1     |
      | import   | 5     |

  Scenario: Extraction of "No Changes" status
    Given the plan indicates the environment is up-to-date
    When the plan is analyzed
    Then the list of resource changes should be empty
    And all change category counts should be zero

  # ============================================================================
  # DIAGNOSTICS AND ERROR HANDLING
  # ============================================================================

  Scenario: Extraction of variable validation errors
    Given the plan failed due to an invalid variable value "oracle-ee"
    When the plan is analyzed
    Then the result should include a diagnostic error
    And the error severity should be "error"
    And the error summary should indicate a variable issue

  Scenario: Extraction of data source resolution errors
    Given the plan failed because a required data source was not found
    When the plan is analyzed
    Then the result should include a diagnostic error
    And the error summary should mention the missing resource

  Scenario: Detection of general execution failures
    Given the plan output indicates an operation failure
    When the plan is analyzed
    Then the plan status should be identified as "failed"
    And the failure details should be captured in diagnostics
