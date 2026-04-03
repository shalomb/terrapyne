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

  Scenario: Aggregate costs across a project
    Given a Terraform Cloud project "finops-project" exists
    And the project "finops-project" contains workspaces with cost estimates totaling $1500 monthly
    When I run "tfc project costs finops-project"
    Then the command should succeed
    And the output should show the total project estimated monthly cost of "$1500.00"
