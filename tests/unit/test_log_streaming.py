"""Unit tests for log streaming pure functions and generator."""

import pytest
import time
from unittest.mock import MagicMock, patch
from terrapyne.cli.run_cmd import _extract_new_lines, _fetch_run_logs_incrementally
from terrapyne.models.run import Run, RunStatus


class TestExtractNewLines:
    """Test offset-tracking logic for incremental log extraction."""

    def test_first_fetch_returns_all_content(self):
        """When previous is empty, all current content should be returned."""
        previous = ""
        current = "Terraform v1.7.0\nPlan: 2 to add"

        result = _extract_new_lines(previous, current)

        assert result == ["Terraform v1.7.0", "Plan: 2 to add"]

    def test_second_fetch_returns_only_delta(self):
        """When previous has content, only new lines should be returned."""
        previous = "Terraform v1.7.0\n"
        current = "Terraform v1.7.0\nPlan: 2 to add\nDone."

        result = _extract_new_lines(previous, current)

        # Only the new content after the previous buffer length
        assert result == ["Plan: 2 to add", "Done."]

    def test_identical_content_returns_empty(self):
        """When content hasn't changed, return empty list."""
        previous = "Terraform v1.7.0\nPlan: 2 to add\n"
        current = "Terraform v1.7.0\nPlan: 2 to add\n"

        result = _extract_new_lines(previous, current)

        assert result == []

    def test_shorter_content_returns_empty(self):
        """When current is shorter than previous, return empty (regression guard)."""
        previous = "Terraform v1.7.0\nPlan: 2 to add\nDone."
        current = "Terraform v1.7.0\n"

        result = _extract_new_lines(previous, current)

        assert result == []


class TestFetchRunLogsIncrementally:
    """Test log streaming generator behavior."""

    def test_generator_is_callable(self):
        """_fetch_run_logs_incrementally should be a generator function."""
        import inspect
        assert inspect.isgeneratorfunction(_fetch_run_logs_incrementally)
