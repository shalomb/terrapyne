Feature: Terraform Resource Details Analysis
  As a DevOps engineer using Terrapyne
  I want to accurately extract resource addresses and attributes from terraform plans
  So I can precisely determine the scope of infrastructure changes

  Background:
    Given a terraform environment is ready
    And a plan is available from a remote execution

  # ============================================================================
  # ADDRESS IDENTIFICATION
  # ============================================================================

  Scenario: Analysis of standard resource addresses
    Given the plan indicates a change for resource "aws_instance.web"
    When the plan is analyzed
    Then the resource should be identified as type "aws_instance"
    And the resource should be identified with name "web"

  Scenario: Analysis of indexed resource addresses
    Given the plan indicates a change for resource "aws_instance.web[0]"
    When the plan is analyzed
    Then the resource should be identified as type "aws_instance"
    And the resource should be identified with name "web"
    And the resource index should be 0

  Scenario: Analysis of module-scoped resources
    Given the plan indicates a change for resource "module.rds.aws_db_instance.db"
    When the plan is analyzed
    Then the resource type should be "aws_db_instance"
    And the resource name should be "db"

  Scenario: Analysis of complex nested resource addresses
    Given the plan indicates a change for resource "module.test[0].aws_instance.web[1]"
    When the plan is analyzed
    Then the resource type should be "aws_instance"
    And the resource name should be "web"

  # ============================================================================
  # ATTRIBUTE EXTRACTION
  # ============================================================================

  Scenario: Extraction of static resource attributes
    Given the plan indicates a new resource with attributes:
      | ami           | "ami-12345" |
      | instance_type | "t2.micro"  |
    When the plan is analyzed
    Then the target state should include "ami" with value "ami-12345"
    And the target state should include "instance_type" with value "t2.micro"

  Scenario: Extraction of modified attributes
    Given the plan indicates an attribute change "~ tags.% = \"2\" -> \"3\""
    When the plan is analyzed
    Then the prior state for "tags.%" should be "2"
    And the target state for "tags.%" should be "3"

  Scenario: Extraction of collection attributes
    Given the plan indicates an array attribute "services = [\"svc1\", \"svc2\"]"
    When the plan is analyzed
    Then the target state for "services" should be a collection
    And the collection should contain 2 elements

  Scenario: Extraction of nested configuration blocks
    Given the plan indicates a nested block "metadata { labels { key = \"value\" } }"
    When the plan is analyzed
    Then the parser should handle the nested structure without errors

  Scenario: Identification of dynamic values
    Given the plan indicates a value will be "computed" or "known after apply"
    When the plan is analyzed
    Then the result should preserve the placeholder marker

  # ============================================================================
  # IMPORT OPERATIONS
  # ============================================================================

  Scenario: Analysis of infrastructure import operations
    Given the plan indicates resource "aws_instance.web" will be imported
    When the plan is analyzed
    Then the operation should be identified as an "import"
