Feature: Debug Mode
  As a DevOps engineer
  I want to trace API calls and see verbose logs
  So I can troubleshoot issues with Terraform Cloud integration

  Scenario: Enable API tracing with --debug flag
    Given I run a command with the "--debug" flag
    When the command makes an API request to Terraform Cloud
    Then the request details should be printed to stderr
    And the response details should be printed to stderr

  Scenario: Debug mode handles API errors gracefully
    Given I run a command with the "--debug" flag
    And the API request will fail with a 404 error
    When I execute the command
    Then the error body should be printed to stderr
    And the command should exit with an error code
