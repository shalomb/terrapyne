"""Tests for SDK namespace and utility functions."""

import os

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


class TestSDKNamespace:
    def test_sdk_imports(self):
        from terrapyne.sdk import TFCClient, RunsAPI, WorkspaceAPI, Plan, Run, Workspace
        assert TFCClient is not None
        assert RunsAPI is not None

    def test_sdk_all_exports(self):
        from terrapyne import sdk
        assert "TFCClient" in sdk.__all__
        assert "Plan" in sdk.__all__
