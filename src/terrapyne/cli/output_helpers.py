"""Output formatting and logging setup for CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terrapyne.rendering.logging import console, error_console

if TYPE_CHECKING:
    from rich.console import Console


def set_console(new_console: Console) -> None:
    console._width = new_console.width
    console.legacy_windows = False
    error_console._width = new_console.width
    error_console.legacy_windows = False
    if hasattr(new_console, "force_terminal"):
        console._force_terminal = new_console.force_terminal
        error_console._force_terminal = new_console.force_terminal
    elif hasattr(new_console, "_force_terminal"):
        console._force_terminal = new_console._force_terminal
        error_console._force_terminal = new_console._force_terminal


def set_quiet_mode(quiet: bool) -> None:
    console.quiet = quiet
    error_console.quiet = quiet


def setup_logging(debug: bool = False) -> None:
    if debug:
        import logging
        import os

        from terrapyne.rendering.logging import MultiFormatter

        os.environ["TERRAPYNE_DEBUG"] = "1"
        logger = logging.getLogger("terrapyne")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(MultiFormatter())
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)


def emit_json(data):
    import json
    from datetime import datetime

    def _default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return str(obj)

    print(json.dumps(data, indent=2, default=_default))
