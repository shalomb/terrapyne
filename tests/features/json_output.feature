Feature: Machine-readable command output

  AI agents and shell pipelines need structured data from CLI commands.

  Rule: JSON output contains no terminal markup

    Scenario: Workspace listing produces parseable JSON
      Given workspaces exist in the organization
      When I request the workspace list as JSON
      Then the output is valid JSON
      And each workspace has an "id" and "name"

    Scenario: Run listing produces parseable JSON
      Given a workspace with runs
      When I request the run list as JSON
      Then the output is valid JSON
      And each run has an "id" and "status"

    Scenario: Project listing produces parseable JSON
      Given projects exist in the organization
      When I request the project list as JSON
      Then the output is valid JSON

    Scenario: Team listing produces parseable JSON
      Given teams exist in the organization
      When I request the team list as JSON
      Then the output is valid JSON
      And each team has an "id" and "name"

  Rule: Single-entity views emit a JSON object

    Scenario: Workspace detail produces a JSON object
      Given workspace "my-app-dev" exists
      When I request the workspace detail as JSON
      Then the output is valid JSON
      And the result is a JSON object with key "id"

    Scenario: Run detail produces a JSON object
      Given a run "run-abc123" exists
      When I request the run detail as JSON
      Then the output is valid JSON
      And the result is a JSON object with key "id"

    Scenario: Project detail produces a JSON object
      Given project "Core Infrastructure" exists
      When I request the project detail as JSON
      Then the output is valid JSON
      And the result is a JSON object with key "id"
