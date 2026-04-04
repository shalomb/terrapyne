Feature: Terraform Plan Parser Integration
  As a DevOps engineer using Terrapyne
  I want to use the plan parser via CLI and Python API

  # ============================================================================
  # TERRAPYNE CLI INTEGRATION
  # ============================================================================

  Scenario: Run parse-plan command with file input
    Given I have a terraform plan output file "plan.txt"
    And the file contains valid terraform plan
    When I run "terrapyne run parse-plan plan.txt"
    Then the command should succeed with exit code 0
    And the output should show parsed plan summary
    And the output should show resource count

  Scenario: Parse plan with JSON output format
    Given I have a terraform plan output file
    When I trigger the parse-plan command with JSON format
    Then the output should be valid JSON output
    And the JSON should contain resource_changes, plan_summary, diagnostics

  Scenario: Parse plan with human-readable output
    Given I have a terraform plan output file
    When I run "terrapyne run parse-plan plan.txt --format human"
    Then the output should be formatted for human readability
    And resources should be listed with addresses and actions

  # ============================================================================
  # PYTHON API INTEGRATION
  # ============================================================================

  Scenario: Use parse_plain_text_plan() method
    Given I have a Terraform instance initialized
    When I call tf.parse_plain_text_plan(plan_text)
    Then the method should return a dictionary
    And the dictionary should contain "resource_changes" key
    And the dictionary should contain "plan_summary" key
    And the dictionary should contain "plan_status" key
