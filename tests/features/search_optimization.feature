Feature: Workspace Search Optimization

  Large TFC organizations have thousands of workspaces. Listing without
  a search term paginates through all of them, which is slow and wasteful.
  The CLI should use wildcard search to narrow results server-side.

  Scenario: Workspace list uses wildcard search parameter
    Given a TFC organization with workspaces
    When I list workspaces with search "prod-*"
    Then the API should receive a wildcard search parameter
    And results should only contain matching workspaces

  Scenario: Workspace list without search warns about large result sets
    Given a TFC organization with workspaces
    When I list workspaces without a search term
    Then I should see a hint to use --search for faster results

  Scenario: Team list uses server-side search
    Given a TFC organization with teams
    When I list teams with search "platform"
    Then the API should use the q= parameter for server-side filtering
