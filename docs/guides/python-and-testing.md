# Python & Testing Guide

Conventions for Python code, typing, imports, and test structure in Terrapyne.

## Python Conventions

### Type Hints

- Always use type hints on function signatures
- Use `from typing import` for complex types (Optional, Union, List, etc.)
- Pydantic models for data validation; leverage `model_construct()` for performance when validation is skipped intentionally
- Document `# type: ignore` with reason when necessary

**Good:**
```python
def get_workspace(self, workspace_id: str) -> Workspace:
    """Fetch workspace by ID."""
    ...

def list_runs(self, workspace_id: str, limit: int = 20) -> tuple[list[Run], int]:
    """List runs; returns (runs, total_count)."""
    ...
```

**Avoid:**
```python
def get_workspace(workspace_id):  # Missing type hints
    ...

def list_runs(workspace_id, limit=20):  # Missing return type
    ...
```

### Imports

- Group imports: stdlib, third-party, local (per isort/ruff conventions)
- Use absolute imports (`from terrapyne.models import Run`)
- Lazy imports for circular dependencies; document why
- No wildcard imports (`from module import *`)

**Good:**
```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from typer import Option

from terrapyne.models.run import Run
```

### Naming

- Constants: `UPPER_SNAKE_CASE`
- Functions/methods: `lower_snake_case`
- Classes: `PascalCase`
- Private: prefix with `_` (e.g., `_internal_method`)
- Enums: `PascalCase` class, `UPPER_SNAKE_CASE` members (e.g., `RunStatus.PENDING`)

### Docstrings

Add docstrings to public functions and classes:
- One-liner describing the function
- Args and Returns sections if not obvious from type hints
- Example usage for non-obvious behavior

**Good:**
```python
def get_active_runs(self, workspace_id: str) -> list[Run]:
    """Fetch runs in active states (pending, running, awaiting_decision).
    
    Args:
        workspace_id: Workspace identifier
        
    Returns:
        List of runs in active states, ordered by creation time (newest first)
    """
    ...
```

## Test Structure

### BDD Tests (Feature Files + Step Definitions)

BDD tests verify end-to-end behavior using Gherkin scenarios.

**Feature file** (`tests/features/workspace.feature`):
```gherkin
Feature: Workspace Management
  As a DevOps engineer
  I want to list and inspect workspaces
  So that I can understand their configuration and health

  Scenario: List all workspaces in organization
    Given I have organization "test-org" set up
    When I list all workspaces
    Then I should see workspace list
    And the list should show workspace count
```

**Step definitions** (`tests/test_cli/test_workspace_commands.py`):
```python
from uv run pytest_bdd import given, when, then, scenario
from unittest.mock import patch, MagicMock

@scenario("../features/workspace.feature", "List all workspaces in organization")
def test_list_workspaces():
    pass

@given('I have organization "test-org" set up')
def org_setup():
    return {"org": "test-org"}

@uv run pytest.fixture
@when("I list all workspaces")
def list_all_workspaces(org_setup, workspace_list_response):
    with patch("terrapyne.cli.workspace_cmd.TFCClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        
        workspaces = [Workspace.from_api_response(data) for data in workspace_list_response["data"]]
        mock_instance.workspaces.list.return_value = (iter(workspaces), 2)
        
        result = runner.invoke(app, ["workspace", "list", "--organization", "test-org"])
        return {"result": result, "workspaces": workspaces}

@then("I should see workspace list")
def check_workspace_list(list_all_workspaces):
    result = list_all_workspaces["result"]
    assert result.exit_code == 0
    assert "my-app-dev" in result.stdout or "my-app-prod" in result.stdout
```

**Key practices:**
- Scenarios describe *business outcomes*, not implementation details
- Steps are outcome-focused: "I should see active run count" (not "emoji 🟢 is present")
- Mock at `TFCClient` level, not httpx
- Use `Mock(spec=...)` for type safety
- Assertions check for presence/absence of information, not exact formatting

**Use skill:** `adzic-index` to audit feature file quality against Specification by Example principles.

### Unit Tests

Unit tests verify isolated functions and models.

**Pattern:**
```python
def test_run_status_is_successful():
    """RunStatus.APPLIED should be considered successful."""
    assert RunStatus.APPLIED.is_successful is True
    assert RunStatus.PLANNED.is_successful is False

def test_workspace_from_api_response_validates_id():
    """Workspace.from_api_response should validate required ID field."""
    with uv run pytest.raises(ValueError):
        Workspace.from_api_response({"attributes": {}})  # Missing ID
```

**Key practices:**
- One assertion per test (or closely related assertions)
- Use fixtures for setup; prefer them to setUp methods
- Mock external dependencies (API, filesystem); test logic, not I/O
- Fast execution: unit tests should run in milliseconds

**Use skill:** `farley-index` to audit test suite against properties: Fast, Honest, Necessary, Maintainable, Atomic, Repeatable.

### Test Fixtures

Reusable test data:

```python
@uv run pytest.fixture
def workspace_detail_response():
    """Mock TFC API response for workspace.show."""
    return {
        "data": {
            "id": "ws-abc123",
            "type": "workspaces",
            "attributes": {
                "name": "my-app-dev",
                "terraform-version": "1.7.0",
                "execution-mode": "remote",
            },
        }
    }

@uv run pytest.fixture
def mock_client():
    """Mock TFCClient for testing."""
    return MagicMock(spec=TFCClient)
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest

# Run a specific test
uv run pytest tests/test_cli/test_workspace_commands.py::test_list_workspaces

# Run with focus (verbose output)
uv run pytest -v -s tests/test_cli/test_workspace_commands.py

# Run fast tests only (exclude UAT)
uv run pytest -m "not uat"

# Run with HTML coverage report
uv run pytest --cov=terrapyne --cov-report=html
```

**Target:** 65% coverage minimum (enforced by pre-commit).

## TDD Workflow

Use the `test-accordion` skill to expand/contract test scope elastically:

1. **Red**: Write a failing test (feature file or unit test)
2. **Green**: Minimal code to make it pass
3. **Refactor**: Improve clarity without changing behavior
4. **Repeat**: Expand scope with next test

Example workflow:
```bash
# Write test for workspace listing
uv run pytest tests/test_cli/test_workspace_commands.py::test_list_workspaces -v

# Code makes it pass
uv run pytest tests/test_cli/test_workspace_commands.py -v

# Add pagination test
uv run pytest tests/test_cli/test_workspace_commands.py::test_list_workspaces_pagination -v

# All pass
uv run pytest tests/test_cli/test_workspace_commands.py -v
```

## Coverage

- Minimum: 65% (enforced by `uv run pytest --cov-fail-under=65`)
- Target: ≥75% for new features
- Exception: Exclude vendored code, test fixtures, CLI shell layer

Run locally before committing:
```bash
uv run pytest --cov=terrapyne --cov-report=term-missing
```

Check HTML report:
```bash
uv run pytest --cov=terrapyne --cov-report=html
# open htmlcov/index.html
```
