# ADR-004: Workspace Dashboard BDD Testing Strategy

**Date:** 2026-04-12  
**Status:** Proposed  
**Relates to:** feat/workspace-dashboard, BDD/TDD practices  

## Context

The workspace-dashboard feature requires writing BDD tests that verify the dashboard displays correct health status, active run counts, and commit information. This ADR documents how to write specification-level BDD tests (per Adzic/Farley criteria) rather than scripted/implementation-focused tests.

## Decision

**BDD tests focus on business outcomes, not implementation details**

### Feature specification (Gherkin)

```gherkin
Feature: Workspace Activity Snapshot
  As a DevOps engineer
  I want a health and activity summary when I inspect a workspace
  So that I can assess its state without opening the GUI

  Scenario: Workspace with recent successful run shows healthy
    Given a workspace with a recently applied run linked to a VCS repository
    When I show the workspace
    Then I should see the workspace health status
    And I should see the count of queued runs
    And I should see the latest commit information

  Scenario: Workspace with no recent runs shows unknown health
    Given a workspace with no run history
    When I show the workspace
    Then I should see that health status is unknown
    And I should see active run count as zero
```

### Step definitions (Python)

```python
@given("a workspace with a recently applied run linked to a VCS repository")
def workspace_with_recent_run(context):
    """Set up a workspace with committed VCS history."""
    # Create workspace mock
    context.workspace = Mock(spec=Workspace)
    context.workspace.id = "ws-123"
    context.workspace.name = "prod-app"
    
    # Create run with successful status and commit info
    context.latest_run = Mock(spec=Run)
    context.latest_run.status = RunStatus.APPLIED
    context.latest_run.commit_sha = "abc123"
    context.latest_run.commit_author = "Alice <alice@example.com>"
    context.latest_run.commit_message = "Enable auto-scaling"
    
    # Mock API to return this run
    context.client.runs.list.return_value = ([context.latest_run], 1)

@when("I show the workspace")
def show_workspace(context):
    """Execute the workspace show command."""
    context.output = StringIO()
    with patch("terrapyne.cli.workspace_cmd.console", new=Console(file=context.output)):
        workspace_show(
            workspace=context.workspace.name,
            organization=context.org,
            output_format="table"
        )

@then("I should see the workspace health status")
def check_health_status(context):
    """Verify health indicator is rendered."""
    output = context.output.getvalue()
    assert "Health & Activity Snapshot" in output or "Healthy" in output
    assert "🟢" in output or "Unhealthy" in output or "Healthy" in output
    # Not asserting emoji literally; focus on outcome (health visible)
```

**Rationale:**

1. **Specification-level, not scripted:** Steps describe *what* the feature does (shows health, shows active count), not *how* (checks for emoji 🟢)
2. **Business language:** "DevOps engineer can assess workspace state" is the goal, not "emoji renders"
3. **Future-proof:** If health indicator changes from emoji to color/text, tests still pass
4. **Resilient to refactoring:** Implementation can change (different table layout, different status wording) without breaking tests
5. **Focused on outcomes:** What matters: health is visible, commit info is shown, counts are accurate

## Pattern Details

### What to test at BDD level

✅ **DO test:**
- Dashboard renders when workspace has runs
- Dashboard shows when no runs exist
- Latest commit information is displayed (if available)
- Active run count is accurate
- JSON output includes snapshot data
- Health status reflects run outcome (success/error/pending)

❌ **DON'T test:**
- Exact emoji characters (🟢 vs 🔴 vs 🟡)
- Table column widths or styling
- "Health & Activity Snapshot" exact header text
- Rich library rendering details
- Specific color codes

### Relationship to unit tests

BDD tests verify **end-to-end behavior**; unit tests verify **components**.

| Level | Focus | Example |
|-------|-------|---------|
| BDD (scenario) | Workspace show displays health snapshot | "Health status is visible in output" |
| Unit (run.py) | RunStatus.is_successful property | `assert RunStatus.APPLIED.is_successful == True` |
| Unit (workspace_cmd.py) | API call is made correctly | `client.runs.list.assert_called_with(ws.id, limit=20, include="configuration-version")` |
| Unit (rich_tables.py) | Dashboard table is constructed | `assert table.title == "Health & Activity Snapshot"` |

BDD tests use mocked API; unit tests verify model logic and API interactions separately.

### Mock setup pattern

```python
def mock_workspace_with_runs(client, run_list):
    """Configure client mock to return runs for list calls."""
    client.runs.list.return_value = (run_list, len(run_list))
    client.runs.get_active_runs.return_value = [r for r in run_list if r.status in RunStatus.get_active_statuses()]
    return client
```

**Key points:**
- Use `Mock(spec=Run)` to get IDE autocomplete
- Set attributes directly (`run.status = RunStatus.APPLIED`)
- Use `RunStatus.get_active_statuses()` for filtering, not hardcoded status strings
- Return tuples matching API signature: `(runs_list, total_count)`

### Test file structure

```python
# tests/test_cli/test_workspace_enrichment_bdd.py

@pytest.mark.bdd
class TestWorkspaceDashboard:
    """BDD tests for workspace activity snapshot feature."""
    
    # Setup fixtures
    @pytest.fixture
    def client_mock(self):
        return Mock(spec=TFCClient)
    
    # Scenarios as test methods
    def test_dashboard_shows_health_when_runs_exist(self, client_mock):
        """Scenario: Workspace with recent successful run shows healthy."""
        # Given
        # When
        # Then
```

Alternatively, use pytest-bdd with .feature files:

```python
# tests/features/workspace_enrichment.feature defines scenarios
# tests/test_cli/test_workspace_enrichment_bdd.py implements step defs
```

## Alternatives Considered

### A1: Test exact output strings
```python
assert "🟢 Healthy (last run applied)" in output
```
- **Rejected:** Brittle; breaks if UI text changes
- Implementation detail, not business requirement

### A2: Mock at httpx level (record API responses)
- **Rejected:** Heavy; requires maintaining response fixtures
- Integration tests should hit real API with UAT marker
- Unit/BDD tests should mock at TFCClient level

### A3: No BDD tests; only unit tests
- **Rejected:** Doesn't test integration of components
- BDD verifies the "happy path" end-to-end

### A4: Test both "exact emoji" and "general health visibility"
- **Rejected:** Redundant; first test is implementation detail
- Focus on what matters: health is visible

## Consequences

**Benefits:**
- Tests document business value (not implementation)
- Resilient to refactoring (emoji → color change won't break tests)
- Easier to onboard non-technical stakeholders (Gherkin is readable)
- Future-proof (if dashboard layout changes, tests still pass)

**Trade-offs:**
- Need separate unit tests to verify emoji/color logic
  - Acceptable; RunStatus enum has dedicated unit tests for emoji property
- BDD tests are higher-level; catch integration bugs but not fine-grained errors
  - Acceptable; unit tests catch component bugs

**Testing pyramid:**
```
        [BDD: 5 scenarios]        ← Feature outcomes
       [Unit: 20-30 tests]       ← Component behavior
      [Integration: UAT marked]  ← Real API (optional)
```

## Implementation checklist

- [ ] Rewrite `tests/features/workspace_enrichment.feature` to Adzic spec level
- [ ] Implement step definitions in `tests/test_cli/test_workspace_enrichment_bdd.py`
- [ ] Use `Mock(spec=...)` for type safety
- [ ] Avoid assertions on emoji/colors; focus on presence/absence
- [ ] Add unit tests for RunStatus enum properties (emoji, is_successful, etc.)
- [ ] Verify BDD tests pass with mocked TFCClient
- [ ] Run full test suite (BDD + unit); verify coverage ≥ 67%

## Related ADRs
- ADR-001: Workspace Dashboard Architecture
- ADR-002: Run Model Enrichment Patterns

## References
- Gherkin syntax: https://cucumber.io/docs/gherkin/
- pytest-bdd: https://pytest-bdd.readthedocs.io/
- Adzic/Farley BDD practices: https://gojko.net/2014/02/07/building-a-specification-framework/
- Implementation: feat/workspace-dashboard branch
