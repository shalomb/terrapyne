Feature: Raw state output for shell scripting

  When developers script: `DB_URL=$(tfc state outputs db_endpoint --raw)`,
  they need the bare unquoted value with no formatting, no ANSI codes.

  Scenario: --raw returns unquoted string value
    Given a workspace with output "db_endpoint" = "postgres://host:5432/db"
    When I run tfc state outputs db_endpoint --raw
    Then stdout is exactly "postgres://host:5432/db"
    And there is no table formatting
    And there are no ANSI escape codes

  Scenario: --raw with non-string value returns JSON representation
    Given a workspace with output "config" = {"host": "db", "port": 5432}
    When I run tfc state outputs config --raw
    Then stdout contains the JSON value

  Scenario: --raw with missing key exits non-zero
    Given a workspace with no output named "missing_key"
    When I run tfc state outputs missing_key --raw
    Then the exit code is 1
    And stderr contains "not found"
