Feature: Configuration Profiles Management
  As a DevOps engineer managing multiple Terraform Cloud organizations and environments
  I want to configure and switch between named profiles
  So that I do not have to repeatedly specify --organization or rely only on directory context

  Scenario: Upward directory hierarchy search for local project profile
    Given a configuration file ".terrapyne.toml" exists in the repository root with profile "acme-corp"
    And the current working directory is a deep subfolder inside the repository
    When I inspect the resolved configuration path
    Then the resolved path points to the root ".terrapyne.toml"
    And the active organization is resolved as "acme-corp"

  Scenario: Falling back to user XDG configuration when no local file exists
    Given no ".terrapyne.toml" file exists in the directory hierarchy
    And an XDG configuration file exists with profile "takeda-prod" for organization "Takeda"
    When I run a command without specifying an organization
    Then the active organization is resolved as "Takeda"

  Scenario: Explicit profile selection via command-line flag
    Given an XDG configuration file contains profiles "staging" and "production"
    When I run "tfc profile show staging"
    Then the profile details for "staging" are displayed

  Scenario: Switching active profile with tfc profile use
    Given a configuration file contains profiles "dev" and "prod"
    When I run "tfc profile use prod"
    Then the command succeeds
    And the current profile is saved as "prod"
