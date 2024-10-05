#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """

import logging
import typing as t
from textwrap import indent
from pretty_traceback.formatting import exc_to_traceback_str


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

Color = t.Union[int, t.Tuple[int, int, int], str]


def _interpret_color(color: Color, offset: int = 0) -> str:
    if isinstance(color, int):
        return f"{38 + offset};5;{color:d}"

    if isinstance(color, (tuple, list)):
        r, g, b = color
        return f"{38 + offset};2;{r:d};{g:d};{b:d}"

    return str(_ansi_colors[color] + offset)


def style(
    text: t.Any,
    fg: t.Optional[Color] = None,
    bg: t.Optional[Color] = None,
    bold: t.Optional[bool] = None,
    dim: t.Optional[bool] = None,
    underline: t.Optional[bool] = None,
    overline: t.Optional[bool] = None,
    italic: t.Optional[bool] = None,
    blink: t.Optional[bool] = None,
    reverse: t.Optional[bool] = None,
    strikethrough: t.Optional[bool] = None,
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
    #
    logging.INFO: "%(message)s",
    #
    logging.WARNING: style("WARN ", fg="yellow") + " | " + style("%(message)s", fg="yellow"),
    #
    logging.ERROR: style("ERROR", fg="red") + " | " + style("%(message)s", fg="red"),
    #
    logging.CRITICAL: style("FATAL", fg="white", bg="red", bold=True) + " | " + style("%(message)s", fg="red", bold=True),
}


class PrettyExceptionFormatter(logging.Formatter):
    """Uses pretty-traceback to format exceptions"""

    def __init__(self, *args, color=True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.color = color

    def formatException(self, ei):
        _, exc_value, traceback = ei
        return exc_to_traceback_str(exc_value, traceback, color=self.color)

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

    def __init__(self, formats: t.Dict[int, str] = None, **kwargs):
        base_format = kwargs.pop("fmt", None)
        super().__init__(base_format, **kwargs)

        formats = formats or default_formats

        self.formatters = {level: PrettyExceptionFormatter(fmt, **kwargs) for level, fmt in formats.items()}

    def format(self, record: logging.LogRecord):
        formatter = self.formatters.get(record.levelno)

        if formatter is None:
            return super().format(record)

        return formatter.format(record)


class LoggingContext:
    def __init__(
        self,
        logger: logging.Logger = None,
        level: int = None,
        handler: logging.Handler = None,
        close: bool = True,
    ):
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
    logger: logging.Logger = None,
    verbose: int = 2,
    filename: str = None,
    file_verbose: int = None,
):
    """
    Use a logging configuration for a CLI application.
    This will prettify log messages for the console, and show more info in a log file.

    Parameters
    ----------
    logger : logging.Logger, default None
        The logger to configure. If None, configures the root logger
    verbose : int from 0 to 3, default 2
        Sets the output verbosity.
        Verbosity 0 shows critical errors
        Verbosity 1 shows warnings and above
        Verbosity 2 shows info and above
        Verbosity 3 and above shows debug and above
    filename : str, default None
        The file name of the log file to log to. If None, no log file is generated.
    file_verbose : int from 0 to 3, default None
        Set a different verbosity for the log file. If None, is set to `verbose`.
        This has no effect if `filename` is None.

    Returns
    -------
    A context manager that will configure the logger, and reset to the previous configuration afterwards.

    Example
    -------
    ```py
    with cli_log_config(verbose=3, filename="test.log"):
        try:
            logging.debug("A debug message")
            logging.info("An info message")
            logging.warning("A warning message")
            logging.error("An error message")
            raise ValueError("A critical message from an exception")
        except Exception as exc:
            logging.critical(str(exc), exc_info=True)
    ```

    will print (with color):
    ```txt
    DEBUG | A debug message
    An info message
    WARN  | A warning message
    ERROR | An error message
    FATAL | A critical message from an exception
        Traceback (most recent call last):
            /home/eb/projects/py-scratch/color-log.py  <module>  288: raise ValueError("A critical message from an exception")
        ValueError: A critical message from an exception
    ```

    and log:
    ```txt
    DEBUG:2022-04-03 15:22:23,528:root:A debug message
    INFO:2022-04-03 15:22:23,528:root:An info message
    WARNING:2022-04-03 15:22:23,528:root:A warning message
    ERROR:2022-04-03 15:22:23,528:root:An error message
    CRITICAL:2022-04-03 15:22:23,528:root:A critical message from an exception
        Traceback (most recent call last):
            /home/eb/projects/py-scratch/color-log.py  <module>  317: raise ValueError("A critical message from an exception")
        ValueError: A critical message from an exception
    ```

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

    # This configuration will print pretty tracebacks with color to the console,
    # and log pretty tracebacks without color to the log file.

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(MultiFormatter())
    console_handler.setLevel(console_level)

    contexts = [
        LoggingContext(logger=logger, level=min(console_level, file_level)),
        LoggingContext(logger=logger, handler=console_handler, close=False),
    ]

    if filename:
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(PrettyExceptionFormatter("%(levelname)s:%(asctime)s:%(name)s:%(message)s", color=False))
        file_handler.setLevel(file_level)
        contexts.append(LoggingContext(logger=logger, handler=file_handler))

    return MultiContext(*contexts)


if __name__ == "__main__":
    with cli_log_config(verbose=3, filename="test.log"):
        try:
            logging.debug("A debug message")
            logging.info("An info message")
            logging.warning("A warning message")
            logging.error("An error message")
            raise ValueError("A critical message from an exception")
        except Exception as exc:
            logging.critical(str(exc), exc_info=True)

# https://gist.github.com/eblocha/fba1c0e2b49333607c4a2d7492f7491c
