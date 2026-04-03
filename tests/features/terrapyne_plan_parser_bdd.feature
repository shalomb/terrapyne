Feature: Terraform Plain Text Plan Parsing in Terrapyne
  As a DevOps engineer using Terrapyne
  I want to parse plain text terraform plan output from Terraform Cloud
  So that I can analyze plans even when terraform plan -json is not available
  And integrate plan analysis into my Terrapyne workflow

  Background:
    Given Terrapyne is initialized with a terraform workspace
    And I have terraform plan output from a remote backend
    And the output may contain ANSI escape codes
    And the output may be incomplete or contain errors

  # ============================================================================
  # SECTION 1: BASIC PLAN PARSING
  # ============================================================================

  Scenario: Parse plan from plain text file
    Given I have a terraform plan output saved to "plan_output.txt"
    When I run "terrapyne parse-plan plan_output.txt"
    Then the command should succeed
    And the output should show plan summary
    And the parsed plan should be stored in memory

  Scenario: Parse plan with resource creation
    Given I have a plain text plan with resource comment "# aws_instance.web will be created"
    And the plan contains resource block with attributes
    When I parse the plan using terrapyne.parse_plain_text_plan()
    Then the parsed plan should contain 1 resource change
    And the resource address should be "aws_instance.web"
    And the resource type should be "aws_instance"
    And the resource name should be "web"
    And the change actions should be ["create"]
    And the change.before should be null or empty
    And the change.after should contain attribute values

  Scenario: Parse plan with resource destruction
    Given I have a plain text plan with resource comment "# aws_instance.web will be destroyed"
    And the plan contains resource block with current attributes
    When I parse the plan using terrapyne.parse_plain_text_plan()
    Then the parsed plan should contain 1 resource change
    And the change actions should be ["delete"]
    And the change.before should contain attribute values
    And the change.after should be null or empty

  Scenario: Parse plan with resource update
    Given I have a plain text plan with resource comment "# aws_instance.web will be updated in-place"
    And the plan contains attribute changes for update
    When I parse the plan using terrapyne.parse_plain_text_plan()
    Then the parsed plan should contain 1 resource change
    And the change actions should be ["update"]
    And the change.before should contain "ami" with value "ami-old"
    And the change.after should contain "ami" with value "ami-new"

  Scenario: Parse plan with resource replacement
    Given I have a plain text plan with resource comment "# aws_instance.web must be replaced"
    And the plan contains "-/+ aws_instance.web (new resource required)"
    When I parse the plan using terrapyne.parse_plain_text_plan()
    Then the parsed plan should contain 1 resource change
    And the change actions should contain "create"
    And the change actions should contain "delete"
    And the change actions should have length 2

  # ============================================================================
  # SECTION 2: TERRAFORM CLOUD (TFC) SPECIFIC HANDLING
  # ============================================================================

  Scenario: Parse TFC output without JSON plan data
    Given I have TFC remote backend terraform plan output
    And the output does NOT support "terraform plan -json"
    And the output does NOT support "terraform plan -out="
    And the output contains plain text only
    When I parse the plan using terrapyne.parse_plain_text_plan()
    Then the parser should successfully extract plan information
    And the parsed plan should contain resource changes
    And the parsed plan should contain plan summary

  Scenario: Parse mixed JSON version message and plain text
    Given I have TFC output starting with JSON version message
    And followed by plain text terraform plan
    When I parse the plan using terrapyne.parse_plain_text_plan()
    Then the parser should skip the JSON version message
    And the parser should extract resources from plain text
    And the parsing should succeed

  Scenario: Handle TFC incomplete plan (errors before completion)
    Given I have TFC output with errors before plan completion
    And the plan contains both resources and validation errors
    When I parse the plan using terrapyne.parse_plain_text_plan()
    Then the parser should extract successfully parsed resources
    And the parser should capture all error diagnostics
    And the plan_status should be "incomplete"
    And both resources and diagnostics should be available

  # ============================================================================
  # SECTION 3: ANSI CODE HANDLING
  # ============================================================================

  Scenario: Strip standard ANSI codes
    Given I have plain text plan with ANSI codes like "[1m  # aws_instance.web[0m"
    When I strip ANSI codes using terrapyne.parse_plain_text_plan()
    Then all ANSI escape sequences should be removed
    And the clean text should be "  # aws_instance.web"
    And the parser should correctly parse the clean text

  Scenario: Strip TFC ANSI format codes
    Given I have TFC output with ANSI codes in format "\x1b[1m...\x1b[0m"
    When I strip ANSI codes
    Then all escape sequences should be removed
    And resource addresses should be correctly extracted
    And resource actions should be correctly identified

  Scenario: Strip GitLab CI ANSI format codes
    Given I have GitLab CI output with ANSI codes in format "\033[1m...\033[0m"
    When I strip ANSI codes
    Then all escape sequences should be removed
    And the parser should process the clean text correctly

  Scenario: Strip mixed ANSI code formats
    Given I have plan output with multiple ANSI code formats
    And includes bracket notation "[1m", real ANSI "\x1b[1m", and GitLab "\033[1m"
    When I strip ANSI codes
    Then all formats should be correctly removed
    And the text should be clean and parseable

  # ============================================================================
  # SECTION 4: RESOURCE ADDRESS PARSING
  # ============================================================================

  Scenario: Parse simple resource address
    Given I have a resource address "aws_instance.web"
    When I parse the plan
    Then the resource type should be "aws_instance"
    And the resource name should be "web"

  Scenario: Parse indexed resource address
    Given I have a resource address "aws_instance.web[0]"
    When I parse the plan
    Then the resource type should be "aws_instance"
    And the resource name should be "web"
    And the resource index should be 0

  Scenario: Parse module resource address
    Given I have a resource address "module.rds.aws_db_instance.db"
    When I parse the plan
    Then the resource type should be "aws_db_instance"
    And the resource name should be "db"
    And the resource address should contain "module.rds"

  Scenario: Parse complex module resource address
    Given I have a resource address "module.test[0].aws_instance.web[1]"
    When I parse the plan
    Then the resource type should be "aws_instance"
    And the resource name should be "web"
    And the address should include both module and resource indices

  Scenario: Parse data source address
    Given I have a data source address "data.aws_ami.example"
    When I parse the plan
    Then the resource type should be "aws_ami"
    And the resource name should be "example"

  # ============================================================================
  # SECTION 5: ATTRIBUTE PARSING
  # ============================================================================

  Scenario: Parse simple key=value attributes
    Given I have a resource with simple attributes
    And "ami = \"ami-12345\""
    And "instance_type = \"t2.micro\""
    When I parse the plan
    Then the change.after should contain "ami" with value "ami-12345"
    And the change.after should contain "instance_type" with value "t2.micro"

  Scenario: Parse attributes with change notation
    Given I have a resource with attribute change "~ tags.% = \"2\" -> \"3\""
    When I parse the plan
    Then the change.before should contain "tags.%" with value "2"
    And the change.after should contain "tags.%" with value "3"

  Scenario: Parse array attributes
    Given I have a resource with array attribute "services = [\"svc1\", \"svc2\"]"
    When I parse the plan
    Then the change.after should contain "services" as an array
    And the array should have 2 elements

  Scenario: Parse map attributes
    Given I have a resource with map attribute "tags = {Environment = \"prod\", Owner = \"team\"}"
    When I parse the plan
    Then the change.after should contain "tags" as a map
    And the map should have "Environment" key

  Scenario: Parse nested attributes
    Given I have a resource with nested attribute "metadata { labels { key = \"value\" } }"
    When I parse the plan
    Then the parser should handle nested structure gracefully
    And the attribute should be parsed or marked as complex

  Scenario: Parse computed value markers
    Given I have a resource with computed value "<computed>"
    When I parse the plan
    Then the attribute value should be preserved as "<computed>"
    And the attribute should not be treated as a regular value

  Scenario: Parse sensitive value markers
    Given I have a resource with sensitive value "(sensitive value)"
    When I parse the plan
    Then the attribute value should be preserved as "(sensitive value)"
    And the sensitive content should not be exposed

  Scenario: Parse known-after-apply markers
    Given I have a resource with known-after-apply value "(known after apply)"
    When I parse the plan
    Then the attribute value should be preserved as "(known after apply)"
    And the attribute should be marked as dynamic

  Scenario: Parse quoted string values
    Given I have attributes with various quote types
    And "name = \"quoted\""
    And "description = 'single quoted'"
    When I parse the plan
    Then quoted values should be stripped of quotes
    And the values should be "quoted" and "single quoted"

  Scenario: Parse numeric values
    Given I have attributes with numeric values
    And "count = 5"
    And "price = 19.99"
    When I parse the plan
    Then numeric values should be parsed as numbers
    And "count" should be integer 5
    And "price" should be float 19.99

  # ============================================================================
  # SECTION 6: PLAN SUMMARY EXTRACTION
  # ============================================================================

  Scenario: Parse plan summary with all change types
    Given I have a plan with summary "Plan: 2 to add, 1 to change, 1 to destroy."
    When I parse the plan
    Then the plan_summary should contain:
      | key     | value |
      | add     | 2     |
      | change  | 1     |
      | destroy | 1     |

  Scenario: Parse plan summary with import operations
    Given I have a plan with summary "Plan: 2 to add, 1 to change, 1 to destroy, 5 to import."
    When I parse the plan
    Then the plan_summary should contain:
      | key     | value |
      | add     | 2     |
      | change  | 1     |
      | destroy | 1     |
      | import  | 5     |

  Scenario: Parse no changes message
    Given I have a plan with message "No changes. Infrastructure is up-to-date."
    When I parse the plan
    Then the resource_changes should be empty
    And the plan_summary should show all zeros
    And the plan_status should be "planned" or "no_changes"

  Scenario: Handle missing plan summary line
    Given I have a plan without "Plan:" summary line
    When I parse the plan
    Then the parser should handle gracefully
    And extracted resources should still be available
    And plan_summary should be null or empty dict

  # ============================================================================
  # SECTION 7: ERROR HANDLING AND DIAGNOSTICS
  # ============================================================================

  Scenario: Extract validation error - Invalid value for variable
    Given I have a plan with error "Error: Invalid value for variable"
    And the error details show "var.engine is \"oracle-ee\""
    When I parse the plan
    Then the diagnostics should contain the error
    And the diagnostic.severity should be "error"
    And the diagnostic.summary should be "Invalid value for variable"
    And the diagnostic.detail should contain the variable info
    And the plan_status should be "failed"

  Scenario: Extract validation error - Unsupported attribute
    Given I have a plan with error "Error: Unsupported attribute"
    And the error shows missing attribute "engine_version"
    When I parse the plan
    Then the diagnostics should contain the error
    And the diagnostic.summary should be "Unsupported attribute"
    And the diagnostic.detail should mention "engine_version"

  Scenario: Extract data source error - Not found
    Given I have a plan with error "Error: no matching RDS DB Subnet Group found"
    And the error location shows "data.aws_db_subnet_group.rds[0]"
    When I parse the plan
    Then the diagnostics should contain the error
    And the diagnostic.summary should contain "no matching"
    And the diagnostic.address should contain "db_subnet_group"

  Scenario: Extract error with file location
    Given I have an error with location "on main.tf line 25, in resource:"
    When I parse the plan
    Then the diagnostic should include range information
    And the range.filename should be "main.tf"
    And the range.start.line should be 25

  Scenario: Extract multiple errors from plan
    Given I have a plan with multiple different error types
    When I parse the plan
    Then the diagnostics should contain all errors
    And each diagnostic should have severity, summary, and detail
    And the diagnostic count should match the errors found

  Scenario: Handle operation failure
    Given I have a plan with "Operation failed: failed running terraform plan (exit 1)"
    When I parse the plan
    Then the plan_status should be "failed"
    And the diagnostics should capture the failure

  Scenario: Handle plan with both resources and errors
    Given I have a plan with parsed resources
    And the plan also contains validation errors
    When I parse the plan
    Then the resource_changes should be populated
    And the diagnostics should be populated
    And the plan_status should be "incomplete"

  # ============================================================================
  # SECTION 8: IMPORT OPERATIONS (BROWNFIELD)
  # ============================================================================

  Scenario: Parse import action in plan
    Given I have a resource with action symbol "<= aws_instance.web"
    When I parse the plan
    Then the change.actions should be ["import"]
    And the change.before should be null (or external state)
    And the change.after should contain the resource state to import

  Scenario: Parse multiple import operations
    Given I have a plan with 5 import operations
    And each has "<= resource_type.name" notation
    When I parse the plan
    Then the resource_changes should contain 5 resources
    And all should have actions ["import"]
    And the plan_summary should show "5 to import"

  Scenario: Parse import with existing attributes
    Given I have an import operation with attributes to import
    When I parse the plan
    Then the resource address should be correct
    And the change.after should contain attributes
    And the resource type should be correctly extracted

  Scenario: Parse read-only data source (similar to import)
    Given I have a resource with action "<= data.aws_ami.example"
    When I parse the plan
    Then the change.actions should be ["read"]
    And the resource type should indicate it's a data source

  # ============================================================================
  # SECTION 9: EDGE CASES AND SPECIAL HANDLING
  # ============================================================================

  Scenario: Handle tainted resources
    Given I have a resource comment "# aws_instance.web (tainted) must be replaced"
    When I parse the plan
    Then the resource should be marked for replacement
    And the change.actions should contain "create" and "delete"

  Scenario: Handle resources with new resource required marker
    Given I have a resource "~ aws_instance.web (new resource required)"
    When I parse the plan
    Then the resource should be correctly parsed
    And the (new resource required) suffix should be removed
    And the actions should be ["create", "delete"]

  Scenario: Handle Windows line endings
    Given I have a plan with Windows line endings "\r\n"
    When I parse the plan
    Then the parser should correctly handle line endings
    And resource_changes should be correctly parsed
    And no parsing errors should occur

  Scenario: Handle very long attribute values
    Given I have a resource with very long attribute values
    And the attribute spans multiple lines
    When I parse the plan
    Then the parser should handle long values gracefully
    And the attribute should be captured completely

  Scenario: Handle special characters in attributes
    Given I have attributes with special characters
    And "description = \"Contains <special> & chars\""
    When I parse the plan
    Then the special characters should be preserved
    And the value should be correctly parsed

  Scenario: Handle empty or minimal plan
    Given I have a minimal plan with no resources
    When I parse the plan
    Then the resource_changes should be empty
    And the parser should not raise exceptions
    And the output should be valid JSON

  # ============================================================================
  # SECTION 10: TERRAPYNE CLI INTEGRATION
  # ============================================================================

  Scenario: Run parse-plan command with file input
    Given I have a terraform plan output file "plan.txt"
    And the file contains valid terraform plan
    When I run "terrapyne parse-plan plan.txt"
    Then the command should succeed with exit code 0
    And the output should show parsed plan summary
    And the output should show resource count
    And the output should show any errors found

  Scenario: Parse plan from stdin
    Given I have terraform plan output piped to stdin
    When I run "cat plan.txt | terrapyne parse-plan"
    Then the command should parse the plan from stdin
    And the output should show the parsed results

  Scenario: Parse plan with JSON output format
    Given I have a terraform plan output file
    When I run "terrapyne parse-plan plan.txt --format json"
    Then the output should be valid JSON output
    And the JSON should contain resource_changes, plan_summary, diagnostics
    And the JSON should be parseable by other tools

  Scenario: Parse plan with human-readable output
    Given I have a terraform plan output file
    When I run "terrapyne parse-plan plan.txt --format human"
    Then the output should be formatted for human readability
    And resources should be listed with addresses and actions
    And errors should be highlighted if present
    And summary should be clearly displayed

  Scenario: Parse plan and display warnings
    Given I have a plan with warnings or known limitations
    When I parse the plan
    Then warnings should be displayed to the user
    And warnings should not block plan parsing
    And the user should understand what was parsed and what wasn't

  Scenario: Parse plan with detailed output
    Given I have a terraform plan output file
    When I run "terrapyne parse-plan plan.txt --verbose"
    Then detailed parsing information should be shown
    And each resource should show full before/after attributes
    And all diagnostics should be detailed

  Scenario: Save parsed plan to file
    Given I have a terraform plan output file
    When I run "terrapyne parse-plan plan.txt --output parsed_plan.json"
    Then the parsed plan should be saved to "parsed_plan.json"
    And the file should contain valid JSON
    And the file should be usable by other tools

  # ============================================================================
  # SECTION 11: PYTHON API INTEGRATION
  # ============================================================================

  Scenario: Use parse_plain_text_plan() method
    Given I have a Terraform instance initialized
    When I call tf.parse_plain_text_plan(plan_text)
    Then the method should return a dictionary
    And the dictionary should contain "resource_changes" key
    And the dictionary should contain "plan_summary" key
    And the dictionary should contain "plan_status" key

  Scenario: Access parsed plan attributes
    Given I have parsed a plan and stored the result
    When I access result["resource_changes"]
    Then I should get a list of resource changes
    And each item should have "address", "type", "name", "change" keys
    And change should have "actions", "before", "after" keys

  Scenario: Access plan summary
    Given I have parsed a plan
    When I access result["plan_summary"]
    Then I should get a dictionary with change counts
    And the dictionary should have keys like "add", "change", "destroy", "import"
    And values should be integers

  Scenario: Access error diagnostics
    Given I have parsed a plan with errors
    When I access result["diagnostics"]
    Then I should get a list of error diagnostics
    And each diagnostic should have "severity", "summary", "detail"
    And diagnostics should include location information if available

  Scenario: Check plan status
    Given I have parsed a plan
    When I check result["plan_status"]
    Then the status should be one of: "planned", "failed", "incomplete"
    And the status should accurately reflect the plan state

  Scenario: Convert parsed plan to PlanInspector format
    Given I have a parsed plan from the parser
    When I pass it to PlanInspector
    Then PlanInspector should accept the format
    And PlanInspector.get_resource_changes() should work
    And PlanInspector assertion methods should work correctly

  # ============================================================================
  # SECTION 12: INTEGRATION WITH OTHER TERRAPYNE FEATURES
  # ============================================================================

  Scenario: Parse local plan after terraform plan
    Given I have run terraform plan in a workspace
    And the output is in plain text format
    When I parse the plan using terrapyne
    Then the parsed result should integrate with validation
    And the parsed result should integrate with run commands
    And the user can decide to proceed with apply based on parsed plan

  Scenario: Analyze plan before TFC run creation
    Given I have a plain text terraform plan
    When I parse and analyze it with terrapyne
    Then I can see what resources will change
    And I can see if there are any errors before triggering TFC run
    And I can make informed decision about running terraform apply

  Scenario: Compare parsed plan with actual TFC run
    Given I have parsed a plain text plan from terraform plan command
    And I trigger a TFC run
    When the TFC run completes
    Then I should be able to compare the parsed plan with TFC results
    And I should see if the actual changes match the plan

  Scenario: Use parsed plan summary in reports
    Given I have parsed multiple plans
    When I collect their plan summaries
    Then I should be able to generate reports showing
    And total resources to be created/changed/destroyed
    And progress tracking across multiple workspaces

  # ============================================================================
  # SECTION 13: ERROR MESSAGES AND USER FEEDBACK
  # ============================================================================

  Scenario: Clear error message for invalid plan file
    Given I provide an invalid or non-existent plan file
    When I run the parse-plan command
    Then I should get a clear error message
    And the message should say the file doesn't exist or is invalid
    And the message should suggest what to do next

  Scenario: Warning for unsupported plan format
    Given I have a plan file that's not plain text
    When I try to parse it
    Then I should get a warning that the format may not be fully supported
    And the parser should attempt to parse anyway
    And I should see what was successfully parsed

  Scenario: Information about parsing limitations
    Given I parse a plan with complex nested structures
    When the parser encounters limitations
    Then I should see informational messages about what couldn't be fully parsed
    And the parser should not fail, but provide best-effort results
    And I should understand what information is available

  Scenario: Success message with summary
    Given I successfully parse a plan
    When the parsing completes
    Then I should see a success message
    And the message should show resource count
    And the message should show error count if any
    And the message should show plan summary (add, change, destroy, import)

  # ============================================================================
  # SECTION 14: PERFORMANCE AND SCALABILITY
  # ============================================================================

  Scenario: Parse plan with 100+ resources
    Given I have a plan with 100+ resource changes
    When I parse the plan
    Then the parsing should complete in reasonable time (<5 seconds)
    And all resources should be extracted
    And memory usage should be acceptable

  Scenario: Handle very large attribute values
    Given I have resources with large attribute blocks
    And some attributes are multi-kilobyte strings
    When I parse the plan
    Then the parser should handle large values efficiently
    And parsing should not timeout or crash

  Scenario: Stream large plan files
    Given I have a very large plan file (>10MB)
    When I parse the plan
    Then the parser should handle large files efficiently
    And memory usage should not spike excessively

  # ============================================================================
  # SECTION 15: BACKWARD COMPATIBILITY
  # ============================================================================

  Scenario: Existing Terraform class functionality unaffected
    Given I have code using existing Terraform class methods
    When I add the plan parser feature
    Then all existing methods should work unchanged
    And existing tests should pass
    And the API should be backward compatible

  Scenario: PlanInspector compatibility
    Given I have code using PlanInspector with terraform show -json output
    When I provide parsed plan from plain text parser
    Then PlanInspector should accept the format without changes
    And all PlanInspector methods should work as before

  Scenario: No breaking changes to CLI
    Given I have scripts using existing terrapyne CLI commands
    When I add the new parse-plan command
    Then existing CLI commands should work unchanged
    And the new command should not conflict with existing ones
