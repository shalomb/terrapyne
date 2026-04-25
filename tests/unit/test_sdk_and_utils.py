"""Tests for SDK namespace and utility functions."""

import os
from unittest.mock import patch

import pytest

from terrapyne.utils import change_directory


class TestChangeDirectory:
    def test_changes_and_restores(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        original = os.getcwd()
        target = tmp_path / "subdir"
        target.mkdir()
        with change_directory(target):
            assert os.path.samefile(os.getcwd(), target)
        assert os.getcwd() == original

    def test_restores_on_exception(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        original = os.getcwd()
        target = tmp_path / "subdir"
        target.mkdir()
        try:
            with change_directory(target):
                raise ValueError("boom")
        except ValueError:
            pass
        assert os.getcwd() == original


class TestValidateContext:
    """Tests for validate_context function from terrapyne.cli.utils."""

    @patch("terrapyne.cli.utils.resolve_organization")
    @patch("terrapyne.cli.utils.resolve_workspace")
    def test_validate_context_returns_workspace_when_provided_without_require_workspace(
        self, mock_resolve_ws, mock_resolve_org
    ):
        """validate_context should return workspace when provided, even if require_workspace=False."""
        from terrapyne.cli.utils import validate_context

        mock_resolve_org.return_value = "my-org"
        mock_resolve_ws.return_value = "my-workspace"

        org, ws = validate_context("my-org", "my-workspace", require_workspace=False)

        assert org == "my-org"
        assert ws == "my-workspace"

    @patch("terrapyne.cli.utils.resolve_organization")
    @patch("terrapyne.cli.utils.resolve_workspace")
    def test_validate_context_returns_none_workspace_when_not_provided_and_not_required(
        self, mock_resolve_ws, mock_resolve_org
    ):
        """validate_context should return None for workspace if not provided and not required."""
        from terrapyne.cli.utils import validate_context

        mock_resolve_org.return_value = "my-org"
        mock_resolve_ws.return_value = None

        org, ws = validate_context("my-org", require_workspace=False)

        assert org == "my-org"
        assert ws is None

    @patch("terrapyne.cli.utils.resolve_organization")
    @patch("terrapyne.cli.utils.resolve_workspace")
    def test_validate_context_returns_workspace_when_required(
        self, mock_resolve_ws, mock_resolve_org
    ):
        """validate_context should return workspace when require_workspace=True."""
        from terrapyne.cli.utils import validate_context

        mock_resolve_org.return_value = "my-org"
        mock_resolve_ws.return_value = "my-workspace"

        org, ws = validate_context("my-org", "my-workspace", require_workspace=True)

        assert org == "my-org"
        assert ws == "my-workspace"

    @patch("terrapyne.cli.utils.resolve_organization")
    @patch("terrapyne.cli.utils.resolve_workspace")
    def test_validate_context_raises_when_workspace_required_but_not_resolved(
        self, mock_resolve_ws, mock_resolve_org
    ):
        """validate_context should raise ValueError if workspace is required but not resolved."""
        from terrapyne.cli.utils import validate_context

        mock_resolve_org.return_value = "my-org"
        mock_resolve_ws.side_effect = ValueError("No workspace detected")

        with pytest.raises(ValueError):
            validate_context("my-org", require_workspace=True)


class TestEmitJson:
    """Tests for emit_json — must serialise real objects, no unittest.mock import."""

    def test_no_unittest_mock_import_in_emit_json(self):
        """emit_json must not import unittest.mock (test-framework leak into production code)."""
        import ast
        import inspect

        from terrapyne.cli.utils import emit_json

        source = inspect.getsource(emit_json)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "unittest" not in alias.name
            if isinstance(node, ast.ImportFrom):
                assert node.module is None or "unittest" not in node.module

    def test_serialises_dict(self, capsys):
        from terrapyne.cli.utils import emit_json

        emit_json({"key": "value"})
        out = capsys.readouterr().out
        assert '"key": "value"' in out

    def test_serialises_datetime(self, capsys):
        from datetime import datetime

        from terrapyne.cli.utils import emit_json

        emit_json({"ts": datetime(2024, 1, 2, 3, 4, 5)})
        out = capsys.readouterr().out
        assert "2024-01-02" in out

    def test_serialises_pydantic_model(self, capsys):
        from pydantic import BaseModel

        from terrapyne.cli.utils import emit_json

        class Thing(BaseModel):
            name: str

        emit_json(Thing(name="hello"))
        out = capsys.readouterr().out
        assert '"hello"' in out


class TestSDKNamespace:
    def test_sdk_imports(self):
        from terrapyne import RunsAPI, TFCClient

        assert TFCClient is not None
        assert RunsAPI is not None

    def test_main_all_exports(self):
        import terrapyne

        assert "TFCClient" in terrapyne.__all__
        assert "Plan" in terrapyne.__all__
