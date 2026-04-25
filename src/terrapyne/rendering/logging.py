#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""Logging utilities and shared console instance."""

from __future__ import annotations

import logging
import typing as t
from datetime import datetime
from textwrap import indent

from pretty_traceback.formatting import exc_to_traceback_str
from rich.console import Console

_ansi_colors = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "reset": 39,
    "bright_black": 90,
    "bright_red": 91,
    "bright_green": 92,
    "bright_yellow": 93,
    "bright_blue": 94,
    "bright_magenta": 95,
    "bright_cyan": 96,
    "bright_white": 97,
}
_ansi_reset_all = "\033[0m"

Color = int | tuple[int, int, int] | str

# Consolidated console instances for CLI output
console = Console()


def _interpret_color(color: Color, offset: int = 0) -> str:
    if isinstance(color, int):
        return f"{38 + offset};5;{color:d}"

    if isinstance(color, (tuple, list)):
        r, g, b = color
        return f"{38 + offset};2;{r:d};{g:d};{b:d}"

    return str(_ansi_colors[color] + offset)


def style(
    text: t.Any,
    fg: Color | None = None,
    bg: Color | None = None,
    bold: bool | None = None,
    dim: bool | None = None,
    underline: bool | None = None,
    overline: bool | None = None,
    italic: bool | None = None,
    blink: bool | None = None,
    reverse: bool | None = None,
    strikethrough: bool | None = None,
    reset: bool = True,
):
    if not isinstance(text, str):
        text = str(text)

    bits = []

    if fg:
        try:
            bits.append(f"\033[{_interpret_color(fg)}m")
        except KeyError:
            raise TypeError(f"Unknown color {fg!r}") from None

    if bg:
        try:
            bits.append(f"\033[{_interpret_color(bg, 10)}m")
        except KeyError:
            raise TypeError(f"Unknown color {bg!r}") from None

    if bold is not None:
        bits.append(f"\033[{1 if bold else 22}m")
    if dim is not None:
        bits.append(f"\033[{2 if dim else 22}m")
    if underline is not None:
        bits.append(f"\033[{4 if underline else 24}m")
    if overline is not None:
        bits.append(f"\033[{53 if overline else 55}m")
    if italic is not None:
        bits.append(f"\033[{3 if italic else 23}m")
    if blink is not None:
        bits.append(f"\033[{5 if blink else 25}m")
    if reverse is not None:
        bits.append(f"\033[{7 if reverse else 27}m")
    if strikethrough is not None:
        bits.append(f"\033[{9 if strikethrough else 29}m")
    bits.append(text)
    if reset:
        bits.append(_ansi_reset_all)
    return "".join(bits)


default_formats = {
    logging.DEBUG: style("DEBUG", fg="cyan") + " | " + style("%(message)s", fg="cyan"),
    logging.INFO: "%(message)s",
    logging.WARNING: style("WARN ", fg="yellow") + " | " + style("%(message)s", fg="yellow"),
    logging.ERROR: style("ERROR", fg="red") + " | " + style("%(message)s", fg="red"),
    logging.CRITICAL: style("FATAL", fg="white", bg="red", bold=True)
    + " | "
    + style("%(message)s", fg="red", bold=True),
}


class PrettyExceptionFormatter(logging.Formatter):
    """Uses pretty-traceback to format exceptions"""

    def __init__(self, *args, color=True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.color = color

    def format_exception(self, ei):
        """Lowercase alias to format exception (linters prefer snake_case)."""
        _, exc_value, traceback = ei
        return exc_to_traceback_str(exc_value, traceback, color=self.color)

    # Maintain logging.Formatter API
    formatException = format_exception

    def format(self, record: logging.LogRecord):
        record.message = record.getMessage()

        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        s = self.formatMessage(record)

        if record.exc_info:
            # Don't assign to exc_text here, since we don't want to inject color all the time
            if s[-1:] != "\n":
                s += "\n"
            # Add indent to indicate the traceback is part of the previous message
            text = indent(self.formatException(record.exc_info), " " * 4)
            s += text

        return s


class MultiFormatter(PrettyExceptionFormatter):
    """Format log messages differently for each log level"""

    def __init__(self, formats: dict[int, str] | None = None, **kwargs) -> None:
        base_format = kwargs.pop("fmt", None)
        super().__init__(base_format, **kwargs)

        formats = formats or default_formats

        self.formatters = {
            level: PrettyExceptionFormatter(fmt, **kwargs) for level, fmt in formats.items()
        }

    def format(self, record: logging.LogRecord):
        formatter = self.formatters.get(record.levelno)

        if formatter is None:
            return super().format(record)

        return formatter.format(record)


class LoggingContext:
    def __init__(
        self,
        logger: logging.Logger | None = None,
        level: int | None = None,
        handler: logging.Handler | None = None,
        close: bool = True,
    ) -> None:
        self.logger = logger or logging.root
        self.level = level
        self.handler = handler
        self.close = close

    def __enter__(self):
        if self.level is not None:
            self.old_level = self.logger.level
            self.logger.setLevel(self.level)

        if self.handler:
            self.logger.addHandler(self.handler)

    def __exit__(self, *exc_info):
        if self.level is not None:
            self.logger.setLevel(self.old_level)

        if self.handler:
            self.logger.removeHandler(self.handler)

        if self.handler and self.close:
            self.handler.close()


class MultiContext:
    """Can be used to dynamically combine context managers"""

    def __init__(self, *contexts) -> None:
        self.contexts = contexts

    def __enter__(self):
        return tuple(ctx.__enter__() for ctx in self.contexts)

    def __exit__(self, *exc_info):
        for ctx in self.contexts:
            ctx.__exit__(*exc_info)


def cli_log_config(
    logger: logging.Logger | None = None,
    verbose: int = 2,
    filename: str | None = None,
    file_verbose: int | None = None,
) -> MultiContext:
    """
    Use a logging configuration for a CLI application.
    This will prettify log messages for the console, and show more info in a log file.
    """

    if file_verbose is None:
        file_verbose = verbose

    verbosities = {
        0: logging.CRITICAL,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
    }

    console_level = verbosities.get(verbose, logging.DEBUG)
    file_level = verbosities.get(file_verbose, logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(MultiFormatter())
    console_handler.setLevel(console_level)

    contexts = [
        LoggingContext(logger=logger, level=min(console_level, file_level)),
        LoggingContext(logger=logger, handler=console_handler, close=False),
    ]

    if filename:
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(
            PrettyExceptionFormatter("%(levelname)s:%(asctime)s:%(name)s:%(message)s", color=False)
        )
        file_handler.setLevel(file_level)
        contexts.append(LoggingContext(logger=logger, handler=file_handler))

    return MultiContext(*contexts)


# https://gist.github.com/eblocha/fba1c0e2b49333607c4a2d7492f7491c


def format_relative_time(dt: datetime) -> str:
    """Format a datetime as a relative time string (e.g., '2h ago')."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)

    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    delta = now - dt

    if delta.days > 365:
        return f"{delta.days // 365}y ago"
    elif delta.days > 30:
        return f"{delta.days // 30}mo ago"
    elif delta.days > 0:
        return f"{delta.days}d ago"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600}h ago"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60}m ago"
    else:
        return "just now"
