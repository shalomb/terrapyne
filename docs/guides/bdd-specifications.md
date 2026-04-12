# BDD Specifications Guide

Writing Adzic-aligned feature files and step definitions using pytest-bdd.

## Specification by Example (Adzic Principles)

BDD tests focus on *business outcomes*, not implementation details. Feature files are living documentation that stakeholders can read and validate.

### The Six Dimensions (Adzic Index)

| Dimension | Question | Good | Avoid |
|-----------|----------|------|-------|
| **Business-Readable** | Would a non-technical stakeholder understand this? | "Workspace shows health status" | "Check if emoji renders" |
| **Intention-Revealing** | Does the scenario explain *why* the feature exists? | "I want to see active runs so I can prioritize my work" | "Test run listing" |
| **Living** | Is the scenario executable? | All steps have implementations | @pending scenarios at ship |
| **Declarative** | Does it describe *what*, not *how*? | "I should see run count" | "Click on 'Runs' tab, verify cell 3" |
| **Focused** | Does each scenario test one behavior? | One scenario per user story | Multiple features per scenario |
| **Atomic** | Can the scenario run independently? | No shared state between scenarios | Tests depend on execution order |

## Writing Feature Files

**Location:** `tests/features/*.feature`

**Template:**
```gherkin
Feature: [Feature Name]
  As a [user role]
  I want to [action/capability]
  So that [business value]

  Background:
    Given [prerequisite setup needed by all scenarios]

  Scenario: [Specific user story / business outcome]
    Given [initial state]
    When [user action]
    Then [expected result]
    And [additional assertions]

  Scenario: [Another specific outcome]
    Given [different initial state]
    When [different action]
    Then [different expected result]
```

**Good example:**
```gherkin
Feature: Workspace Activity Dashboard
  As a DevOps engineer
  I want to see a health and activity summary when I inspect a workspace
  So that I can assess its state without opening the GUI

  Scenario: Workspace with recent successful run shows healthy status
    Given a workspace with a recently applied run
    When I show the workspace details
    Then I should see the workspace health snapshot
    And I should see the active run count

  Scenario: Workspace with no run history shows unknown health
    Given a workspace with no runs
    When I show the workspace details
    Then I should see unknown health status
    And I should see zero active runs
```

**Avoid:**
```gherkin
Feature: Test workspace commands
  # Why? Vague; doesn't explain business value

  Scenario: Workspace show test
    # Why? Vague action/outcome
    Given I set up a workspace context
    When I invoke the workspace show CLI command
    Then the exit code should be 0
    And the output should contain workspace name in the correct column format
    # Why? Implementation-scripted; tests UI, not business outcome
```

### Scenario Guidelines

| Do | Reason | Example |
|----|--------|---------|
| Use present tense | Reads naturally | "When I show the workspace" (not "showed") |
| Use "I" for user actions | Empathy; first-person perspective | "I should see" (not "user should see") |
| Describe outcomes, not steps | Business-focused | "health snapshot is visible" (not "emoji 🟢 renders") |
| One assertion per Then | Clear pass/fail | "Then I should see health status" |
| Use tables for data | Readable examples | `\| aws_instance.web \|` |
| Use concrete values | Testable | "workspace my-app-dev" (not "a workspace") |

## Writing Step Definitions

**Location:** `tests/test_cli/test_*_bdd.py`

**Pattern:**
```python
from pytest_bdd import given, scenario, then, when, parsers
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

runner = CliRunner()

# Scenario wrapper
@scenario("../features/workspace.feature", "Workspace with recent successful run shows healthy status")
def test_dashboard_healthy():
    pass

# Given: Setup (not a fixture)
@given("a workspace with a recently applied run")
def workspace_with_recent_run():
    """Establish initial state; does not execute CLI."""
    pass

# When: Action (fixture returning context)
@pytest.fixture
@when("I show the workspace details")
def show_workspace_details(workspace_detail_response, run_list_response):
    """Execute the CLI command and capture output."""
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        
        workspace = Workspace.from_api_response(workspace_detail_response["data"])
        runs = [Run.from_api_response(data) for data in run_list_response["data"]]
        
        mock_instance.workspaces.get.return_value = workspace
        mock_instance.runs.list.return_value = (runs, len(runs))
        
        result = runner.invoke(app, ["workspace", "show", "my-app-dev", "--organization", "test-org"])
        
        return {"result": result, "workspace": workspace, "runs": runs}

# Then: Assertions (outcome-focused)
@then("I should see the workspace health snapshot")
def check_health_snapshot(show_workspace_details):
    """Verify health information is present."""
    result = show_workspace_details["result"]
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    
    # Outcome: health status is visible
    output_lower = result.stdout.lower()
    assert any(
        keyword in output_lower
        for keyword in ["health", "status", "snapshot", "state"]
    ), "Health snapshot not found in output"
```

### Mocking Strategy

**Mock at TFCClient level, not httpx:**
```python
# ✅ GOOD: Mock the high-level client
with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
    mock_instance = MagicMock()
    mock_client.return_value.__enter__.return_value = mock_instance
    mock_instance.workspaces.get.return_value = workspace
    # Now test the CLI command

# ❌ AVOID: Mocking httpx directly
with patch("httpx.Client") as mock_http:
    # Hard to maintain, tightly coupled to implementation
```

**Use `Mock(spec=...)` for type safety:**
```python
# ✅ GOOD: IDE autocomplete, catches typos
mock_run = Mock(spec=Run)
mock_run.status = RunStatus.APPLIED
mock_run.id = "run-abc123"

# ❌ AVOID: No type safety
mock_run = MagicMock()
mock_run.status = RunStatus.APPLIED
```

### Assertion Guidelines

| Outcome-Focused | Implementation-Scripted | Why Prefer |
|-----------------|------------------------|-----------|
| "I should see active run count" | "Check if cell contains count" | Tests behavior, not UI |
| "Health status is visible" | "Emoji 🟢 is present" | Resilient to design changes |
| "Commit SHA is displayed" | "Substring matches 40 hex chars" | Focuses on outcome |
| "Output is valid JSON" | "JSON has 'snapshot' key at level 3" | Less brittle |

**Good example:**
```python
@then("I should see the latest run information")
def check_latest_run_info(show_workspace_dashboard):
    result = show_workspace_dashboard["result"]
    runs = show_workspace_dashboard["runs"]
    
    assert result.exit_code == 0
    # Outcome: latest run is present in output
    if runs:
        latest_run = runs[0]
        assert (
            latest_run.id in result.stdout
            or "run" in result.stdout.lower()
        ), "Latest run information not found"
```

## Feature File Checklist

Before committing a feature file:

- [ ] User persona is clear (who is the actor?)
- [ ] Business value is stated (why does this matter?)
- [ ] Scenario titles are specific (not generic "test X")
- [ ] Each Given/When/Then is a complete sentence
- [ ] No implementation details (buttons, exact text, emoji)
- [ ] Scenarios are independent (can run in any order)
- [ ] All steps have implementations (no orphaned steps)
- [ ] Coverage includes happy path, error cases, edge cases

## Evaluating BDD Quality

Use the `adzic-index` skill to audit feature files:
```bash
# In Claude Code:
/adzic-index tests/features/workspace.feature
```

This scores your feature file on:
- Business-Readable: Would stakeholders understand?
- Intention-Revealing: Does intent shine through?
- Living: Are all steps executable?
- Declarative: Is it outcome-focused?
- Focused: One behavior per scenario?
- Atomic: Can scenarios run independently?

Target: **≥7.0/10** for release-ready features.

## Related Resources

- [ADR-004: Workspace Dashboard Testing Strategy](../architecture/ADR-004-workspace-dashboard-testing.md)
- [Python & Testing Guide](python-and-testing.md)
- Gojko Adzic: [Specification by Example](https://gojko.net/2014/02/07/building-a-specification-framework/)
- pytest-bdd: [Documentation](https://pytest-bdd.readthedocs.io/)
