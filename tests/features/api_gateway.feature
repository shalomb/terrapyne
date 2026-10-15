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

  Scenario: Querying a regional European Union endpoint
    Given the TFC API returns a workspace configuration for "example-app-workspace" in "my-eu-org"
    When I run "tfc api /organizations/{organization}/workspaces/example-app-workspace -o my-eu-org -H app.eu.terraform.io"
    Then the command succeeds
    And the request was sent to host "app.eu.terraform.io"

  Scenario: Querying with URL parameters on GET
    Given the TFC API returns a list of workspaces for "my-org"
    When I run "tfc api /organizations/{organization}/workspaces -o my-org -F search[name]=prod -F page[size]=25"
    Then the command succeeds
    And the request query params contained "page[size]" with 25
    And the request query params contained "search[name]" with "prod"

  Scenario: Handling 204 No Content responses cleanly
    Given the TFC API accepts deletion of workspace "ws-old" returning empty body
    When I run "tfc api -X DELETE /workspaces/ws-old -o my-org"
    Then the command succeeds

