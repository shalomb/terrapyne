#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for project configuration."""

import tomllib
from pathlib import Path


class TestPyprojectToml:
    """Test pyproject.toml configuration."""

    def test_coverage_gate_at_67_percent(self):
        """Verify the coverage gate is set to 67%."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        pytest_config = config.get("tool", {}).get("pytest", {}).get("ini_options", {})
        addopts = pytest_config.get("addopts", "")

        # Find the --cov-fail-under value
        cov_fail_under_value = None
        if isinstance(addopts, str):
            import re

            match = re.search(r"--cov-fail-under=(\d+)", addopts)
            if match:
                cov_fail_under_value = int(match.group(1))

        assert cov_fail_under_value == 67, (
            f"Expected coverage gate of 67, got {cov_fail_under_value}"
        )
