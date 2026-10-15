"""Unit tests for agent session-gated deletions (safety.py)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import typer

from terrapyne.cli.safety import (
    check_deletion_allowed,
    is_deletion_granted,
)


class TestIsDeletionGranted:
    """Test grant string evaluation against resource classes."""

    def test_no_grant_set(self):
        assert is_deletion_granted("workspace", env={}) is False

    def test_empty_grant(self):
        assert is_deletion_granted("workspace", env={"TERRAPYNE_ALLOW_DELETE": ""}) is False

    def test_single_matching_grant(self):
        env = {"TERRAPYNE_ALLOW_DELETE": "workspace"}
        assert is_deletion_granted("workspace", env=env) is True
        assert is_deletion_granted("var", env=env) is False

    def test_multiple_grants_with_whitespace(self):
        env = {"TERRAPYNE_ALLOW_DELETE": " workspace , var , team "}
        assert is_deletion_granted("workspace", env=env) is True
        assert is_deletion_granted("var", env=env) is True
        assert is_deletion_granted("team", env=env) is True
        assert is_deletion_granted("trigger", env=env) is False

    def test_case_insensitive_matching(self):
        env = {"TERRAPYNE_ALLOW_DELETE": "WORKSPACE"}
        assert is_deletion_granted("workspace", env=env) is True
        assert is_deletion_granted("WORKSPACE", env={"TERRAPYNE_ALLOW_DELETE": "workspace"}) is True

    def test_wildcard_all_grant(self):
        env = {"TERRAPYNE_ALLOW_DELETE": "all"}
        assert is_deletion_granted("workspace", env=env) is True
        assert is_deletion_granted("var", env=env) is True
        assert is_deletion_granted("team", env=env) is True
        assert is_deletion_granted("api", env=env) is True
        assert is_deletion_granted("anything", env=env) is True


class TestCheckDeletionAllowed:
    """Test gating enforcement logic across human and agent contexts."""

    def test_human_terminal_is_unconditionally_allowed(self):
        # stdout is a TTY and no agent env vars
        env = {}
        # Should return cleanly without raising
        check_deletion_allowed("workspace", env=env, stdout_isatty=True)

    def test_agent_context_refuses_when_no_grant(self):
        # Non-TTY stdout implies agent/automation
        env = {}
        with pytest.raises(typer.Exit) as exc:
            check_deletion_allowed("workspace", env=env, stdout_isatty=False)
        assert exc.value.exit_code == 1

    def test_agent_context_allows_when_matching_grant_present(self):
        env = {"TERRAPYNE_ALLOW_DELETE": "workspace"}
        # Should not raise
        check_deletion_allowed("workspace", env=env, stdout_isatty=False)

    def test_agent_context_allows_when_wildcard_all_present(self):
        env = {"TERRAPYNE_ALLOW_DELETE": "all"}
        check_deletion_allowed("workspace", env=env, stdout_isatty=False)
        check_deletion_allowed("var", env=env, stdout_isatty=False)
        check_deletion_allowed("api", env=env, stdout_isatty=False)

    def test_agent_context_refuses_when_different_grant_present(self):
        env = {"TERRAPYNE_ALLOW_DELETE": "var"}
        with pytest.raises(typer.Exit) as exc:
            check_deletion_allowed("workspace", env=env, stdout_isatty=False)
        assert exc.value.exit_code == 1

    def test_refusal_emits_guidance_to_error_console(self):
        env = {"CI": "true"}
        with patch("terrapyne.cli.safety.error_console.print") as mock_print:
            with pytest.raises(typer.Exit):
                check_deletion_allowed("workspace", env=env, stdout_isatty=True)
            mock_print.assert_called()
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "Refusal:" in printed_text
            assert "workspace" in printed_text
            assert "tfc harness exec --allow-delete=workspace" in printed_text
