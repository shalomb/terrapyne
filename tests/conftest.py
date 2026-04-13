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


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "bdd: BDD-style scenario tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "cli: CLI command tests")
    config.addinivalue_line("markers", "api: API layer tests")
