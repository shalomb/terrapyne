"""Error handling decorators for CLI commands."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import typer

from terrapyne.core.exceptions import TerrapyneError, TFCAPIError
from terrapyne.rendering.logging import error_console

F = TypeVar("F", bound=Callable[..., Any])


def handle_cli_errors(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            raise
        except TFCAPIError as e:
            status = f" ({e.status_code})" if e.status_code else ""
            error_console.print(f"[red]API Error{status}:[/red] {e}")
            if e.response is not None:
                errors = None
                if isinstance(e.response, dict):
                    errors = e.response.get("errors")
                else:
                    try:
                        errors = e.response.json().get("errors")
                    except Exception:
                        pass
                if errors:
                    for err in errors:
                        title = err.get("title", "")
                        detail = err.get("detail", "")
                        if title:
                            error_console.print(f"  [red]•[/red] [bold]{title}[/bold]")
                        if detail:
                            error_console.print(f"    {detail}")
            raise typer.Exit(code=1) from None
        except (TerrapyneError, ValueError) as e:
            error_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1) from None
        except Exception as e:
            error_console.print(f"[red]Unexpected error:[/red] {e}")
            raise typer.Exit(code=1) from None

    return wrapper  # type: ignore
