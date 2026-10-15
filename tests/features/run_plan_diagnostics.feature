Feature: Plan Diagnostics and Module Health Alerts in Run Show
  As a DevOps engineer inspecting Terraform runs
  I want to see plan diagnostics and module health alerts directly in run show
  So that I am immediately aware of deprecated modules and configuration issues without hunting through logs

  Background:
    Given a terraform cloud organization is accessible

  Scenario: Run with deprecated modules surfaces health alerts
    Given a finished run "run-dep123" with deprecated module alerts in its plan log
    When I run "tfc run show run-dep123"
    Then the output should display "Module Health Alerts"
    And the output should list the deprecated module "app.terraform.io/Takeda/EC2/aws" and version "1.4.0"
    And exit code should be 0

  Scenario: Run with no diagnostics displays clean summary
    Given a finished run "run-clean123" with no diagnostics in its plan log
    When I run "tfc run show run-clean123"
    Then the output should not display "Module Health Alerts"
    And the output should not display "Error Diagnostic"
    And exit code should be 0

  Scenario: Run with diagnostics exported as JSON
    Given a finished run "run-dep123" with deprecated module alerts in its plan log
    When I run "tfc run show run-dep123 --format json"
    Then the JSON output should contain a "diagnostics" list
    And the diagnostics should include category "module_health"
    And exit code should be 0

  Scenario: Skipping diagnostics with --no-diagnostics
    Given a finished run "run-dep123" with deprecated module alerts in its plan log
    When I run "tfc run show run-dep123 --no-diagnostics"
    Then the output should not display "Module Health Alerts"
    And no plan logs should be fetched
    And exit code should be 0

  Scenario: Errored run surfaces error diagnostic details
    Given an errored run "run-err123" with an error diagnostic in its plan log
    When I run "tfc run show run-err123"
    Then the output should display "Error Diagnostic"
    And the output should show the diagnostic error summary "Missing required argument"
    And exit code should be 0

  Scenario: Dedicated diagnostics command displays module health alerts
    Given a finished run "run-dep123" with deprecated module alerts in its plan log
    When I run "tfc run diagnostics run-dep123"
    Then the output should display "Module Health Alerts"
    And the output should list the deprecated module "app.terraform.io/Takeda/EC2/aws" and version "1.4.0"
    And exit code should be 0

  Scenario: Dedicated diagnostics command exported as JSON
    Given a finished run "run-dep123" with deprecated module alerts in its plan log
    When I run "tfc run diagnostics run-dep123 --format json"
    Then the output should be a JSON array with diagnostics
    And exit code should be 0

  Scenario: Dedicated diagnostics command filtered by category
    Given a finished run "run-dep123" with deprecated module alerts in its plan log
    When I run "tfc run diagnostics run-dep123 --category module_health"
    Then the output should display "Module Health Alerts"
    And exit code should be 0

  Scenario: Dedicated diagnostics command filtered by severity
    Given a finished run "run-dep123" with deprecated module alerts in its plan log
    When I run "tfc run diagnostics run-dep123 --severity warning"
    Then the output should display "Module Health Alerts"
    And exit code should be 0

  Scenario: Dedicated diagnostics command for clean run
    Given a finished run "run-clean123" with no diagnostics in its plan log
    When I run "tfc run diagnostics run-clean123"
    Then the output should display "No diagnostics reported"
    And exit code should be 0
