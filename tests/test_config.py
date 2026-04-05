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
        addopts = pytest_config.get("addopts", [])

        # Find the --cov-fail-under value (it's a combined string like "--cov-fail-under=80")
        cov_fail_under_value = None
        for opt in addopts:
            if isinstance(opt, str) and "--cov-fail-under" in opt:
                if "=" in opt:
                    cov_fail_under_value = int(opt.split("=")[1])
                break

        assert cov_fail_under_value == 67, f"Expected coverage gate of 67, got {cov_fail_under_value}"
