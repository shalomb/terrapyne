Feature: Run error summary extraction
  As a DevOps engineer
  I want to see the actual Terraform error message for an errored run
  So I can diagnose failures without manually fetching logs

  Background:
    Given a RunsAPI instance with a mock client

  Scenario: Plan-stage failure — error extracted from plan log
    Given a run "run-plan-fail" is errored with plan status "errored"
    And the plan log contains:
      """
      Error: creating EC2 Instance: OptInRequired: not subscribed to this service
      """
    When I get the error summary for the run
    Then the summary contains "OptInRequired"
    And only the plan log was fetched

  Scenario: Apply-stage failure — plan succeeded, error extracted from apply log
    Given a run "run-apply-fail" is errored with plan status "finished"
    And the apply log contains:
      """
      Error: creating RDS DB Subnet Group (tec-db-default-defra): DBSubnetGroupAlreadyExists
      """
    When I get the error summary for the run
    Then the summary contains "DBSubnetGroupAlreadyExists"
    And only the apply log was fetched

  Scenario: Multiple errors in apply log — all are returned
    Given a run "run-multi-fail" is errored with plan status "finished"
    And the apply log contains:
      """
      Error: creating RDS DB Subnet Group (tec-db-default-defra): DBSubnetGroupAlreadyExists
      Error: creating RDS DB Subnet Group (tec-db-default-euw1): DBSubnetGroupAlreadyExists
      """
    When I get the error summary for the run
    Then the summary contains "tec-db-default-defra"
    And the summary contains "tec-db-default-euw1"

  Scenario: No logs available — falls back to run message
    Given a run "run-no-logs" is errored with plan status "errored"
    And no plan log is available
    When I get the error summary for the run
    Then the summary contains the run message

  Scenario: Run has no plan — returns run message
    Given a run "run-no-plan" is errored with no plan ID
    When I get the error summary for the run
    Then the summary contains the run message

  Scenario: Apply-stage failure with unknown plan status — apply log tried first
    Given a run "run-none-status" is errored with plan status unknown and an apply ID
    And the apply log contains:
      """
      Error: creating Lambda Function: InvalidParameterValueException: The provided execution role does not have permissions
      """
    When I get the error summary for the run
    Then the summary contains "InvalidParameterValueException"
    And the apply log was fetched before the plan log

  Scenario: Apply-stage failure with unknown plan status — empty apply log falls back to plan log
    Given a run "run-none-fallback" is errored with plan status unknown and an apply ID
    And the apply log is empty
    And the plan log contains:
      """
      Error: plan stage error
      """
    When I get the error summary for the run
    Then the summary contains "plan stage error"
    And the apply log was fetched before the plan log
