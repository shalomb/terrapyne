"""CLI tests for workspace triggers commands."""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.run_trigger import RunTrigger

runner = CliRunner()
runner.mix_stderr = True
runner.mix_stderr = True


# ============================================================================
# Shared context fixture
# ============================================================================


@pytest.fixture
def ctx():
    return {}


# ============================================================================
# Scenario: Listing upstream run triggers for a workspace
# ============================================================================


@scenario("../features/workspace_triggers.feature", "Listing upstream run triggers for a workspace")
def test_list_triggers():
    pass


@given('I have organization "test-org" and workspace "ws-downstream"')
def given_org_and_workspace(ctx):
    ctx["org"] = "test-org"
    ctx["workspace"] = "ws-downstream"


@when('I run "workspace triggers list ws-downstream"')
def when_list_triggers(ctx):
    trigger = MagicMock(spec=RunTrigger)
    trigger.id = "rt-abc123"
    trigger.source_workspace_id = "ws-up1"
    trigger.source_workspace_name = "upstream-workspace"
    trigger.created_at = None

    with (
        patch("terrapyne.cli.context_helpers.resolve_organization", return_value="test-org"),
        patch(
            "terrapyne.cli.workspace_cmd.validate_context",
            return_value=("test-org", "ws-downstream"),
        ),
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_instance.workspaces.get.return_value = MagicMock(id="ws-downstream-id")
        mock_instance.run_triggers.list.return_value = [trigger]

        result = runner.invoke(
            app, ["workspace", "triggers", "list", "ws-downstream", "--organization", "test-org"]
        )
        ctx["result"] = result


@then('the output should list the upstream trigger source "upstream-workspace"')
def then_output_lists_trigger(ctx):
    assert ctx["result"].exit_code == 0, ctx["result"].output
    assert "upstream-workspace" in ctx["result"].output


# ============================================================================
# Scenario: Adding a run trigger from an upstream workspace
# ============================================================================


@scenario(
    "../features/workspace_triggers.feature", "Adding a run trigger from an upstream workspace"
)
def test_add_trigger():
    pass


@when('I add a trigger with source "upstream-workspace"')
def when_add_trigger(ctx):
    trigger = MagicMock(spec=RunTrigger)
    trigger.id = "rt-new1"
    trigger.source_workspace_id = "ws-up1"
    trigger.source_workspace_name = "upstream-workspace"

    with (
        patch("terrapyne.cli.context_helpers.resolve_organization", return_value="test-org"),
        patch(
            "terrapyne.cli.workspace_cmd.validate_context",
            return_value=("test-org", "ws-downstream"),
        ),
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_instance.workspaces.get.return_value = MagicMock(id="ws-downstream-id")
        upstream_ws = MagicMock(id="ws-up1")
        mock_instance.workspaces.get.side_effect = [
            MagicMock(id="ws-downstream-id"),
            upstream_ws,
        ]
        mock_instance.run_triggers.add.return_value = trigger

        result = runner.invoke(
            app,
            [
                "workspace",
                "triggers",
                "add",
                "ws-downstream",
                "--source",
                "upstream-workspace",
                "--organization",
                "test-org",
            ],
        )
        ctx["result"] = result


@then("the trigger should be created successfully")
def then_trigger_created(ctx):
    assert ctx["result"].exit_code == 0, ctx["result"].output
    assert "upstream-workspace" in ctx["result"].output or "trigger" in ctx["result"].output.lower()


# ============================================================================
# Scenario: Removing a run trigger
# ============================================================================


@scenario("../features/workspace_triggers.feature", "Removing a run trigger")
def test_remove_trigger():
    pass


@given('there is an existing trigger "rt-abc123"')
def given_existing_trigger(ctx):
    ctx["trigger_id"] = "rt-abc123"


@when('I remove trigger "rt-abc123"')
def when_remove_trigger(ctx):
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization", return_value="test-org"),
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_instance.run_triggers.remove.return_value = None

        result = runner.invoke(
            app,
            [
                "workspace",
                "triggers",
                "remove",
                "--trigger-id",
                "rt-abc123",
                "--organization",
                "test-org",
                "--force",
            ],
        )
        ctx["result"] = result


@then("the trigger should be removed successfully")
def then_trigger_removed(ctx):
    assert ctx["result"].exit_code == 0, ctx["result"].output


# ============================================================================
# Scenario: Listing triggers shows empty state
# ============================================================================


@scenario(
    "../features/workspace_triggers.feature",
    "Listing triggers shows empty state when no triggers exist",
)
def test_list_triggers_empty():
    pass


@when("I list triggers for a workspace with no triggers")
def when_list_no_triggers(ctx):
    with (
        patch("terrapyne.cli.context_helpers.resolve_organization", return_value="test-org"),
        patch(
            "terrapyne.cli.workspace_cmd.validate_context",
            return_value=("test-org", "ws-downstream"),
        ),
        patch("terrapyne.api.client.TFCClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_instance.workspaces.get.return_value = MagicMock(id="ws-downstream-id")
        mock_instance.run_triggers.list.return_value = []

        result = runner.invoke(
            app, ["workspace", "triggers", "list", "ws-downstream", "--organization", "test-org"]
        )
        ctx["result"] = result


@then("the output should indicate no triggers configured")
def then_no_triggers(ctx):
    assert ctx["result"].exit_code == 0, ctx["result"].output
    assert "No" in ctx["result"].output or "no" in ctx["result"].output
