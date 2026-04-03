"""Model utilities and helpers."""

from datetime import datetime


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 datetime string from API response.

    The TFC API returns datetime strings in ISO 8601 format with 'Z' timezone
    indicator. This function handles that format and returns a proper datetime.

    Args:
        value: ISO 8601 datetime string, or None.
            Example: "2025-03-13T07:50:15.781Z"

    Returns:
        Parsed datetime object with UTC timezone, or None if value is None.

    Examples:
        >>> parse_iso_datetime("2025-03-13T07:50:15.781Z")
        datetime.datetime(2025, 3, 13, 7, 50, 15, 781000, tzinfo=datetime.timezone.utc)

        >>> parse_iso_datetime(None)
        None
    """
    if not value:
        return None
    # Replace 'Z' with '+00:00' for proper timezone parsing
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
