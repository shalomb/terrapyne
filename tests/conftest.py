#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""Pytest configuration and shared fixtures.

This module provides:
- Common fixtures for all tests
- pytest-bdd setup and configuration
- API response fixtures for mocking
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.factories import (
    error_forbidden,
    error_not_found,
    error_unauthorized,
    project_list_response,
    project_response,
    run_list_response,
    run_response,
    team_project_access_list_response,
    team_project_access_response,
    team_response,
    variable_response,
    workspace_list_response,
    workspace_response,
    workspace_variables_response,
)

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture()
def tf_required_version():
    out = subprocess.run(["terraform", "version"], capture_output=True, shell=False)
    if out.returncode != 0:
        pytest.skip("terraform binary not available")
    if m := re.search("\\d\\.\\d[^ \n]+", out.stdout.decode()):
        return m.group(0)


@pytest.fixture
def fixtures_dir(tmp_path_factory) -> Path:
    """Return path to fixtures directory."""
    # Provide a fixtures directory path relative to tests/fixtures
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def plan_parser_fixtures() -> dict[str, str]:
    """Cache all plan fixture files keyed by stem.

    Returns dict mapping fixture stem (e.g., 'basic_create.stdout') to file content.
    """
    fixture_dir = Path(__file__).parent / "fixtures" / "plan_outputs"
    fixtures = {}

    if fixture_dir.exists():
        for fixture_file in sorted(fixture_dir.glob("*.txt")):
            stem = fixture_file.stem
            fixtures[stem] = fixture_file.read_text()

    return fixtures


@pytest.fixture
def temp_terraform_dir(tmp_path: Path) -> Path:
    """Create temporary directory for Terraform files."""
    return tmp_path / "terraform"


# ============================================================================
# pytest-bdd Configuration
# ============================================================================

# Register API response fixtures
pytest_plugins = ["tests.fixtures.api_responses"]


# Backwards-compatible fixtures (wrap factories for existing test code)
@pytest.fixture
def factory_workspace_response():
    """Factory fixture for workspace responses."""
    return workspace_response


@pytest.fixture
def factory_workspace_list_response():
    """Factory fixture for workspace list responses."""
    return workspace_list_response


@pytest.fixture
def factory_variable_response():
    """Factory fixture for variable responses."""
    return variable_response


@pytest.fixture
def factory_workspace_variables_response():
    """Factory fixture for workspace variable list responses."""
    return workspace_variables_response


@pytest.fixture
def factory_run_response():
    """Factory fixture for run responses."""
    return run_response


@pytest.fixture
def factory_run_list_response():
    """Factory fixture for run list responses."""
    return run_list_response


@pytest.fixture
def factory_project_response():
    """Factory fixture for project responses."""
    return project_response


@pytest.fixture
def factory_project_list_response():
    """Factory fixture for project list responses."""
    return project_list_response


@pytest.fixture
def factory_team_response():
    """Factory fixture for team responses."""
    return team_response


@pytest.fixture
def factory_team_project_access_response():
    """Factory fixture for team project access responses."""
    return team_project_access_response


@pytest.fixture
def factory_team_project_access_list_response():
    """Factory fixture for team project access list responses."""
    return team_project_access_list_response


@pytest.fixture
def factory_error_not_found():
    """Factory fixture for not found errors."""
    return error_not_found


@pytest.fixture
def factory_error_unauthorized():
    """Factory fixture for unauthorized errors."""
    return error_unauthorized


@pytest.fixture
def factory_error_forbidden():
    """Factory fixture for forbidden errors."""
    return error_forbidden


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "bdd: BDD-style scenario tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "cli: CLI command tests")
    config.addinivalue_line("markers", "api: API layer tests")


@pytest.fixture(autouse=True)
def setup_console():
    """Snapshot and restore the shared Rich console singletons around every test.

    The singletons ``terrapyne.rendering.logging.console`` and ``error_console``
    carry mutable state (``quiet``, ``_force_terminal``, ``no_color``, ``_width``)
    that production code and other tests legitimately mutate via ``set_console``,
    ``set_quiet_mode``, and ``configure_for_agent_context``.

    Without restoration, mutations leak across tests and produce order-dependent
    failures (one test sets ``console.quiet = True``; the next test sees a quiet
    console and fails an output assertion). See EPIC-001 in PLAN.md.

    This fixture:
    1. Snapshots the six relevant attributes on both consoles.
    2. Configures a fresh forced-terminal console for the test (matches the
       behaviour the previous version of this fixture provided).
    3. Restores the snapshot after the test, regardless of pass/fail.

    The ``setup_console`` name is preserved for backwards compatibility with
    tests that depend on it as a fixture.
    """
    from rich.console import Console

    from terrapyne.cli.output_helpers import set_console
    from terrapyne.rendering.logging import console, error_console

    _MUTABLE_ATTRS = ("quiet", "_force_terminal", "no_color", "_width", "legacy_windows")

    def _snapshot(c):
        return {attr: getattr(c, attr, None) for attr in _MUTABLE_ATTRS}

    def _restore(c, snap):
        for attr, value in snap.items():
            try:
                setattr(c, attr, value)
            except AttributeError:
                # Some attributes are read-only on Rich's Console; skip silently.
                pass

    snap_console = _snapshot(console)
    snap_error = _snapshot(error_console)

    new_console = Console(force_terminal=True, width=100)
    set_console(new_console)

    try:
        yield new_console
    finally:
        _restore(console, snap_console)
        _restore(error_console, snap_error)


@pytest.fixture(autouse=True)
def default_human_context(request):
    """Prevent real agent env vars (e.g. CLAUDECODE=1) from affecting tests.

    By default all tests run as if the CLI is invoked by a human at a terminal.
    Tests that specifically need agent context patch configure_for_agent_context
    themselves (see test_agent_context_cli_bdd.py).
    """
    # Tests in agent_context_cli_bdd manage their own patching — skip there.
    if "agent_context_cli" in request.module.__name__:
        yield
        return

    from unittest.mock import patch

    from terrapyne.cli.agent_context import AgentContext

    human_ctx = AgentContext(is_agent=False, reason=None)
    # Patch where configure_for_agent_context is *used* (main.py imports it by name)
    with patch("terrapyne.cli.main.configure_for_agent_context", return_value=human_ctx):
        yield
