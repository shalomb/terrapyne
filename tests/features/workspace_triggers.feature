Feature: Workspace run triggers management
  As a DevOps engineer using Terraform Cloud
  I want to inspect and manage workspace-to-workspace run trigger relationships
  So that I can debug pipeline failures and control automation flows

  Background:
    Given I have organization "test-org" and workspace "ws-downstream"

  Scenario: Listing upstream run triggers for a workspace
    When I run "workspace triggers list ws-downstream"
    Then the output should list the upstream trigger source "upstream-workspace"

  Scenario: Adding a run trigger from an upstream workspace
    When I add a trigger with source "upstream-workspace"
    Then the trigger should be created successfully

  Scenario: Removing a run trigger
    Given there is an existing trigger "rt-abc123"
    When I remove trigger "rt-abc123"
    Then the trigger should be removed successfully

  Scenario: Listing triggers shows empty state when no triggers exist
    When I list triggers for a workspace with no triggers
    Then the output should indicate no triggers configured
