Feature: Response Caching
  As a DevOps engineer
  I want the CLI to cache API responses
  So I can reduce latency and stay within API rate limits

  Scenario: Enable caching with --cache-ttl flag
    Given I run a command with the "--cache-ttl 60" flag
    When I request workspace details twice
    Then the second request should be served from the cache
    And the total number of API calls should be reduced
