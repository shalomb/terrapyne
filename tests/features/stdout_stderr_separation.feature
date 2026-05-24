Feature: stdout carries data, stderr carries human text
  As an automation author
  I want clean separation between machine output and human output
  So that piping JSON to jq always works, even on errors

  Scenario: A successful read command writes JSON to stdout only
    Given a command that supports --format json
    When the command runs successfully
    Then stdout contains valid JSON
    And stderr is empty or contains only progress messages

  Scenario: A failing read command emits error text to stderr
    Given an organization name that does not exist
    When I run "tfc workspace list -o ghost --format json"
    Then stdout is either empty or contains valid JSON
    And stderr contains the human-readable error
    And the exit code is non-zero

  Scenario: Progress messages do not contaminate JSON output
    Given a command that prints progress hints in TTY mode
    When stdout is redirected to a file and --format json is used
    Then the file contains exactly one valid JSON document
