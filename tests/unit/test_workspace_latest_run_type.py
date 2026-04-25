"""Tests that Workspace.latest_run is typed as Run | None, not Any."""

import typing


def test_workspace_latest_run_annotation_is_run_or_none():
    """Workspace.latest_run field annotation must be Run | None, not Any."""
    from terrapyne.models.run import Run
    from terrapyne.models.workspace import Workspace

    # Pass localns so forward refs resolve correctly at runtime
    hints = typing.get_type_hints(Workspace, localns={"Run": Run})
    latest_run_hint = hints.get("latest_run")

    assert latest_run_hint is not None, "Workspace must have a latest_run annotation"

    # Must not be Any
    assert latest_run_hint is not typing.Any, (
        "Workspace.latest_run must not be typed as Any — use Run | None"
    )

    # Must be Optional[Run] / Run | None
    args = typing.get_args(latest_run_hint)
    assert Run in args, (
        f"Workspace.latest_run must include Run in its type args, got: {latest_run_hint}"
    )
    assert type(None) in args, (
        f"Workspace.latest_run must be nullable (None), got: {latest_run_hint}"
    )


def test_workspace_latest_run_no_circular_import_at_runtime():
    """Importing Workspace must not trigger circular import errors at runtime."""
    # If this import succeeds without error, there's no circular import
    from terrapyne.models.workspace import Workspace  # noqa: F401

    assert True
