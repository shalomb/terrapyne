Feature: Raw TFC API Gateway
  As an automation script or coding agent
  I want to make authenticated HTTP requests to any Terraform Cloud API endpoint
  So that I can interact with unmodeled endpoints and inspect raw responses without handling tokens or curl

  Scenario: Querying an endpoint with organization placeholder
    Given the TFC API returns a workspace configuration for "example-app-workspace" in "my-eu-org"
    When I run "tfc api /organizations/{organization}/workspaces/example-app-workspace -o my-eu-org"
    Then the command succeeds
    And the JSON output contains workspace attribute "name" with value "example-app-workspace"

  Scenario: Auto-detecting organization context for template placeholders
    Given the local workspace context resolves organization "detected-org"
    And the TFC API returns a list of workspaces for "detected-org"
    When I run "tfc api /organizations/{organization}/workspaces"
    Then the command succeeds
    And the request was sent to "/organizations/detected-org/workspaces"

  Scenario: Mutating a resource with custom HTTP method and body fields
    Given the TFC API accepts an action for workspace "ws-123"
    When I run "tfc api -X POST /workspaces/ws-123/actions/lock -F reason=Maintenance"
    Then the command succeeds
    And the request method was "POST"
    And the request payload contained "reason" with "Maintenance"

  Scenario: Surfacing API errors with non-zero exit and structured stderr
    Given the TFC API returns a 404 error for "/nonexistent"
    When I run "tfc api /nonexistent"
    Then the command exits with code 1
    And stderr indicates the resource was not found
