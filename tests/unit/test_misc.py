import logging
import sys

from terrapyne.rendering.logging import (
    PrettyExceptionFormatter,
    _interpret_color,
    cli_log_config,
    style,
)


def test_interpret_color_and_style_basic():
    assert _interpret_color(5).startswith("38")
    assert _interpret_color((1, 2, 3)).startswith("38")
    assert _interpret_color("red") == str(31)
    s = style("hello", fg="red", bold=True, reset=False)
    assert "hello" in s
    assert "\033" in s


def test_pretty_exception_formatter():
    try:
        raise ValueError("boom")
    except Exception:
        ei = sys.exc_info()
    pf = PrettyExceptionFormatter(color=False)
    out = pf.format_exception(ei)
    assert "ValueError" in out


def test_cli_log_config_captures_logs(capsys):
    with cli_log_config(verbose=3):
        logging.error("an error occurred")
    captured = capsys.readouterr()
    assert "ERROR" in captured.err or "ERROR" in captured.out
