"""Unit tests for the tfc api gateway helper functions."""

import json
import re
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from terrapyne.cli.api_cmd import (
    get_subcommand_hint,
    interpolate_endpoint,
    load_request_payload,
    parse_field_options,
)
from terrapyne.cli.main import app


def test_interpolate_endpoint_with_placeholders():
    endpoint = "/organizations/{organization}/workspaces/{workspace}"
    result = interpolate_endpoint(endpoint, organization="acme-corp", workspace="my-ws")
    assert result == "/organizations/acme-corp/workspaces/my-ws"


def test_interpolate_endpoint_with_shorthand_placeholders():
    endpoint = "/organizations/{org}/workspaces/{ws}"
    result = interpolate_endpoint(endpoint, organization="acme-corp", workspace="my-ws")
    assert result == "/organizations/acme-corp/workspaces/my-ws"


def test_interpolate_endpoint_with_colon_placeholders():
    endpoint = "/organizations/:organization/workspaces/:workspace"
    result = interpolate_endpoint(endpoint, organization="acme-corp", workspace="my-ws")
    assert result == "/organizations/acme-corp/workspaces/my-ws"


def test_interpolate_endpoint_missing_org_raises():
    endpoint = "/organizations/{organization}/workspaces/test"
    with pytest.raises(
        ValueError,
        match=re.escape("Organization could not be resolved for '{organization}' placeholder"),
    ):
        interpolate_endpoint(endpoint, organization=None, workspace=None)


def test_parse_field_options():
    fields = ["name=production", "auto_apply=true", "count=10"]
    result = parse_field_options(fields)
    assert result["name"] == "production"
    assert result["auto_apply"] is True
    assert result["count"] == 10


def test_interpolate_endpoint_missing_workspace_raises():
    endpoint = "/organizations/acme/workspaces/{workspace}"
    with pytest.raises(
        ValueError,
        match=re.escape("Workspace could not be resolved for '{workspace}' placeholder"),
    ):
        interpolate_endpoint(endpoint, organization="acme", workspace=None)


def test_parse_field_options_extended():
    fields = [
        "name=production",
        "auto_apply=false",
        "rate=3.14",
        "tag=null",
        'nested={"sub": 1}',
    ]
    result = parse_field_options(fields)
    assert result["name"] == "production"
    assert result["auto_apply"] is False
    assert result["rate"] == 3.14
    assert result["tag"] is None
    assert result["nested"] == {"sub": 1}


def test_parse_field_options_invalid():
    with pytest.raises(ValueError, match="Invalid field format"):
        parse_field_options(["invalid_field_without_equals"])


def test_load_request_payload_from_json_string():
    payload = load_request_payload('{"key": "value"}')
    assert payload == {"key": "value"}


def test_load_request_payload_from_file(tmp_path):
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps({"foo": "bar"}))
    payload = load_request_payload(str(payload_file))
    assert payload == {"foo": "bar"}


def test_load_request_payload_from_stdin(monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO('{"stdin_key": 42}'))
    payload = load_request_payload("-")
    assert payload == {"stdin_key": 42}


def test_load_request_payload_invalid_json():
    with pytest.raises(ValueError, match="Failed to parse JSON payload"):
        load_request_payload("{broken json")


def test_load_request_payload_non_dict():
    with pytest.raises(ValueError, match="Payload must be a JSON object"):
        load_request_payload("[1, 2, 3]")


def test_api_command_paginate(monkeypatch):
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.paginate.return_value = iter([{"id": "ws-1"}, {"id": "ws-2"}])

    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        result = runner.invoke(
            app, ["api", "/organizations/{organization}/workspaces", "--paginate", "-o", "test-org"]
        )
        raw_json = result.stdout if result.stdout else result.output
        data = json.loads(raw_json)
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "ws-1"


def test_api_command_raw_output(monkeypatch):
    runner = CliRunner()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"raw": true}'
    mock_resp.json.return_value = {"raw": True}
    mock_client._request.return_value = mock_resp

    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        result = runner.invoke(app, ["api", "/status", "--raw", "-o", "test-org"])
        assert result.exit_code == 0
        assert '{"raw": true}' in result.output


def test_api_command_normalizes_leading_slash():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {}
    mock_client._request.return_value = mock_resp

    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        # Call without leading slash
        result = runner.invoke(app, ["api", "organizations/test-org/workspaces", "-o", "test-org"])
        assert result.exit_code == 0
        called_path = mock_client._request.call_args.kwargs["path"]
        assert called_path == "/organizations/test-org/workspaces"


def test_api_command_input_file_with_field_override(tmp_path):
    runner = CliRunner()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {}
    mock_client._request.return_value = mock_resp

    payload_file = tmp_path / "req.json"
    payload_file.write_text(json.dumps({"name": "base", "version": 1}))

    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        result = runner.invoke(
            app,
            [
                "api",
                "-X",
                "POST",
                "/workspaces",
                "-i",
                str(payload_file),
                "-F",
                "version=2",
                "-o",
                "test-org",
            ],
        )
        assert result.exit_code == 0
        sent_json = mock_client._request.call_args.kwargs["json_data"]
        assert sent_json["name"] == "base"
        assert sent_json["version"] == 2


def test_api_command_stdin_input():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {}
    mock_client._request.return_value = mock_resp

    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        result = runner.invoke(
            app,
            ["api", "-X", "POST", "/workspaces", "--input", "-", "-o", "test-org"],
            input='{"streamed": true}',
        )
        assert result.exit_code == 0
        sent_json = mock_client._request.call_args.kwargs["json_data"]
        assert sent_json == {"streamed": True}


def test_api_command_non_json_response():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "plain text log or diagnostic"
    mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    mock_client._request.return_value = mock_resp

    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        result = runner.invoke(app, ["api", "/logs", "-o", "test-org"])
        assert result.exit_code == 0
        assert "plain text log or diagnostic" in result.output


def test_get_subcommand_hint_matches():
    assert "tfc workspace list" in (
        get_subcommand_hint("GET", "/organizations/my-org/workspaces") or ""
    )
    assert "tfc workspace create" in (
        get_subcommand_hint("POST", "/organizations/my-org/workspaces") or ""
    )
    assert "tfc workspace show" in (
        get_subcommand_hint("GET", "/organizations/my-org/workspaces/my-ws") or ""
    )
    assert "tfc workspace show" in (get_subcommand_hint("GET", "/workspaces/ws-123") or "")
    assert "tfc workspace update" in (get_subcommand_hint("PATCH", "/workspaces/ws-123") or "")
    assert "tfc workspace delete" in (get_subcommand_hint("DELETE", "/workspaces/ws-123") or "")
    assert "tfc workspace lock" in (
        get_subcommand_hint("POST", "/workspaces/ws-123/actions/lock") or ""
    )
    assert "tfc workspace unlock" in (
        get_subcommand_hint("POST", "/workspaces/ws-123/actions/unlock") or ""
    )
    assert "tfc run list" in (get_subcommand_hint("GET", "/workspaces/ws-123/runs") or "")
    assert "tfc run create" in (get_subcommand_hint("POST", "/runs") or "")
    assert "tfc run show" in (get_subcommand_hint("GET", "/runs/run-123") or "")
    assert "tfc run apply" in (get_subcommand_hint("POST", "/runs/run-123/actions/apply") or "")
    assert "tfc run cancel" in (get_subcommand_hint("POST", "/runs/run-123/actions/discard") or "")
    assert "tfc state current" in (
        get_subcommand_hint("GET", "/workspaces/ws-123/current-state-version") or ""
    )
    assert "tfc project list" in (
        get_subcommand_hint("GET", "/organizations/my-org/projects") or ""
    )
    assert "tfc team list" in (get_subcommand_hint("GET", "/organizations/my-org/teams") or "")
    assert "tfc varset list" in (get_subcommand_hint("GET", "/organizations/my-org/varsets") or "")
    assert "tfc vcs list" in (
        get_subcommand_hint("GET", "/organizations/my-org/oauth-clients") or ""
    )


def test_get_subcommand_hint_no_match():
    assert get_subcommand_hint("GET", "/status") is None
    assert get_subcommand_hint("GET", "/api/v2/ping") is None
    assert get_subcommand_hint("POST", "/unknown/custom/endpoint") is None


def test_api_command_emits_subcommand_hint():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {}
    mock_client._request.return_value = mock_resp

    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        result = runner.invoke(
            app, ["api", "/organizations/{organization}/workspaces", "-o", "test-org"]
        )
        assert result.exit_code == 0
        stderr = result.stderr if hasattr(result, "stderr") and result.stderr else result.output
        assert "hint:" in stderr
        assert "tfc workspace list" in stderr


def test_api_command_suppresses_hint_with_no_hints_flag():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {}
    mock_client._request.return_value = mock_resp

    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        result = runner.invoke(
            app, ["api", "/organizations/{organization}/workspaces", "-o", "test-org", "--no-hints"]
        )
        assert result.exit_code == 0
        stderr = result.stderr if hasattr(result, "stderr") and result.stderr else ""
        assert "hint:" not in stderr


def test_api_command_suppresses_hint_with_env(monkeypatch):
    runner = CliRunner()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {}
    mock_client._request.return_value = mock_resp

    monkeypatch.setenv("TERRAPYNE_NO_HINTS", "1")
    with (
        patch("terrapyne.cli.api_cmd.get_client") as get_client_mock,
        patch("terrapyne.cli.api_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client_mock.return_value.__enter__.return_value = mock_client
        result = runner.invoke(
            app, ["api", "/organizations/{organization}/workspaces", "-o", "test-org"]
        )
        assert result.exit_code == 0
        stderr = result.stderr if hasattr(result, "stderr") and result.stderr else ""
        assert "hint:" not in stderr
