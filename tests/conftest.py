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
