"""Tests for handle_cli_errors deep error context surfacing."""

from unittest.mock import MagicMock

import pytest
from click.exceptions import Exit

from terrapyne.cli.error_handlers import handle_cli_errors
from terrapyne.core.exceptions import TFCAPIError


@handle_cli_errors
def _dummy():
    """Decorated function that raises whatever is injected."""
    raise _dummy._exc  # type: ignore[attr-defined]


class TestHandleCliErrorsDeepContext:
    """handle_cli_errors surfaces structured TFC API error details on stderr."""

    def test_dict_response_with_errors(self, capsys):
        _dummy._exc = TFCAPIError(
            "forbidden",
            status_code=403,
            response={"errors": [{"title": "Forbidden", "detail": "Team lacks access"}]},
        )
        with pytest.raises(Exit):
            _dummy()
        err = capsys.readouterr().err
        assert "Forbidden" in err
        assert "Team lacks access" in err

    def test_response_object_with_json_method(self, capsys):
        resp = MagicMock()
        resp.json.return_value = {"errors": [{"title": "Not Found", "detail": "ws gone"}]}
        _dummy._exc = TFCAPIError("not found", status_code=404, response=resp)
        with pytest.raises(Exit):
            _dummy()
        err = capsys.readouterr().err
        assert "Not Found" in err
        assert "ws gone" in err

    def test_response_json_raises_does_not_crash(self, capsys):
        resp = MagicMock()
        resp.json.side_effect = ValueError("bad json")
        _dummy._exc = TFCAPIError("bad", status_code=500, response=resp)
        with pytest.raises(Exit):
            _dummy()
        err = capsys.readouterr().err
        assert "API Error (500)" in err

    def test_no_response_still_exits(self, capsys):
        _dummy._exc = TFCAPIError("oops", status_code=422, response=None)
        with pytest.raises(Exit):
            _dummy()
        err = capsys.readouterr().err
        assert "API Error (422)" in err
        assert "oops" in err
