"""Unit tests for the tfc api gateway helper functions."""

import json
import re
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from terrapyne.cli.api_cmd import (
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
        assert result.exit_code == 0
        data = json.loads(result.output)
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
