Feature: SDK pagination is honest
  As an SDK consumer
  I want list APIs to either paginate or to advertise their page-size
  So I never silently lose data

  Scenario: runs.list with limit > 100 returns up to limit items
    Given a workspace with 250 runs
    When I call client.runs.list(workspace_id, limit=200)
    Then the result contains 200 runs
    And the total count metadata reports 250

  Scenario: runs.list with limit None fetches all available runs
    Given a workspace with 250 runs
    When I call client.runs.list(workspace_id, limit=None)
    Then the result contains 250 runs

  Scenario: runs.list with limit <= 100 uses a single page
    Given a workspace with 50 runs
    When I call client.runs.list(workspace_id, limit=20)
    Then the result contains 20 runs
    And only one API request was made
