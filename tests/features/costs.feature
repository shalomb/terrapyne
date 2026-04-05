Feature: Cost Estimates
  As a FinOps engineer or DevOps engineer
  I want to view cost estimates for my infrastructure
  So that I can control my cloud spend without needing the GUI

  Scenario: Extract workspace costs from the latest plan
    Given a Terraform Cloud workspace "finops-prod" exists
    And the latest run for "finops-prod" has a cost estimate of $500 monthly with a $50 delta
    When I run "tfc workspace costs finops-prod"
    Then the command should succeed
    And the output should show an estimated monthly cost of "$500.00"
    And the output should show a cost delta of "+$50.00"

  Scenario: Extract workspace costs with a cost decrease
    Given a Terraform Cloud workspace "finops-dev" exists
    And the latest run for "finops-dev" has a cost estimate of $300 monthly with a -$20 delta
    When I run "tfc workspace costs finops-dev"
    Then the command should succeed
    And the output should show an estimated monthly cost of "$300.00"
    And the output should show a cost delta of "-$20.00"

  Scenario: Extract workspace costs with zero delta
    Given a Terraform Cloud workspace "finops-test" exists
    And the latest run for "finops-test" has a cost estimate of $150 monthly with a $0 delta
    When I run "tfc workspace costs finops-test"
    Then the command should succeed
    And the output should show an estimated monthly cost of "$150.00"
    And the output should show a cost delta of "$0.00"

  Scenario: Extract workspace costs when no cost estimate is available
    Given a Terraform Cloud workspace "finops-staging" exists
    And the latest run for "finops-staging" has no cost estimate
    When I run "tfc workspace costs finops-staging"
    Then the command should succeed
    And the output should indicate no cost estimates are available

  Scenario: Extract workspace costs with invalid cost strings
    Given a Terraform Cloud workspace "finops-invalid" exists
    And the latest run for "finops-invalid" has an invalid cost estimate string
    When I run "tfc workspace costs finops-invalid"
    Then the command should succeed
    And the output should show an estimated monthly cost of "$0.00"
    And the output should show a cost delta of "$0.00"

  Scenario: Aggregate costs across a project
    Given a Terraform Cloud project "finops-project" exists
    And the project "finops-project" contains workspaces with cost estimates totaling $1500 monthly
    When I run "tfc project costs finops-project"
    Then the command should succeed
    And the output should show the total project estimated monthly cost of "$1,500.00"

  Scenario: Aggregate costs across a project with no workspaces
    Given a Terraform Cloud project "empty-project" exists
    And the project "empty-project" contains no workspaces
    When I run "tfc project costs empty-project"
    Then the command should succeed
    And the output should show the total project estimated monthly cost of "$0.00"

  Scenario: Aggregate costs across a project with invalid cost strings
    Given a Terraform Cloud project "invalid-project" exists
    And the project "invalid-project" contains workspaces with invalid cost estimates
    When I run "tfc project costs invalid-project"
    Then the command should succeed
    And the output should show the total project estimated monthly cost of "$0.00"
