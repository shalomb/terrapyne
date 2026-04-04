Feature: Terraform Plain Text Plan Parsing Core
  As a DevOps engineer using Terrapyne
  I want to analyze infrastructure changes from standard terraform output
  So that I can understand plan impact even without JSON data

  Background:
    Given a terraform environment is ready
    And a plan is available from a remote execution

  # ============================================================================
  # CHANGE DETECTION
  # ============================================================================

  Scenario: Detection of infrastructure additions
    Given the plan indicates a new resource "aws_instance.web" will be created
    When the plan is analyzed
    Then the result should confirm 1 resource will be added
    And the change address should be "aws_instance.web"

  Scenario: Detection of infrastructure removals
    Given the plan indicates resource "aws_instance.web" will be destroyed
    When the plan is analyzed
    Then the result should confirm 1 resource will be deleted

  Scenario: Detection of in-place updates
    Given the plan indicates resource "aws_instance.web" will be modified
    When the plan is analyzed
    Then the result should confirm 1 resource will be updated

  Scenario: Detection of resource replacements
    Given the plan indicates resource "aws_instance.web" must be replaced
    When the plan is analyzed
    Then the result should confirm a replacement operation for "aws_instance.web"
    And the actions should include both creation and deletion

  # ============================================================================
  # OUTPUT SANITIZATION
  # ============================================================================

  Scenario: Cleanup of formatted terminal output
    Given the plan output contains terminal formatting codes (ANSI)
    When the plan is sanitized
    Then all formatting codes should be removed
    And the underlying plan text should be preserved

  Scenario: Handling of platform-specific line endings
    Given the plan was generated on a system with Windows line endings
    When the plan is analyzed
    Then the parser should normalize the line endings
    And the resource changes should be correctly identified

  # ============================================================================
  # ROBUSTNESS
  # ============================================================================

  Scenario: Analysis of minimal or empty plans
    Given the plan indicates no changes are required
    When the plan is analyzed
    Then the list of resource changes should be empty
    And the analysis should complete without errors

  Scenario: Analysis of mixed metadata and plan text
    Given the output begins with technical version metadata
    And is followed by the actual infrastructure plan
    When the plan is analyzed
    Then the metadata should be ignored
    And the infrastructure changes should be successfully extracted
