"""BDD steps for `tfc vcs set-repo`."""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.workspace import Workspace
from tests.fixtures.factories import workspace_response

scenarios("../features/vcs_set_repo.feature")

runner = CliRunner()


def _ws(identifier: str | None) -> Workspace:
    vcs = (
        {
            "identifier": identifier,
            "branch": "main",
            "repository-http-url": f"https://github.com/{identifier}",
            "oauth-token-id": "ot-abc123",
        }
        if identifier
        else None
    )
    resp = workspace_response(name="ws", vcs_repo=vcs)
    if identifier is None:
        resp["data"]["attributes"]["vcs-repo"] = None  # factory defaults to a repo otherwise
    return Workspace.from_api_response(resp["data"])


@pytest.fixture
def api():
    return MagicMock()


@given(parsers.parse('workspace "{name}" is connected to repository "{identifier}"'))
def _connected(api, identifier):
    api.workspaces.get.return_value = _ws(identifier)
    api.workspaces.set_vcs_repo.return_value = _ws("myorg/new-name")


@given(parsers.parse('workspace "{name}" has no VCS repository connected'))
def _no_vcs(api):
    api.workspaces.get.return_value = _ws(None)


@when(parsers.parse('I run "{command}"'), target_fixture="result")
def _run(api, command):
    argv = command.split()[1:]
    with (
        patch("terrapyne.cli.vcs_cmd.get_client") as get_client,
        patch("terrapyne.cli.vcs_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client.return_value.__enter__.return_value = api
        return runner.invoke(app, [*argv, "--organization", "test-org"])


@then(parsers.parse('the output should show "{a}" and "{b}"'))
def _shows(result, a, b):
    assert a in result.output and b in result.output


@then("no change should be sent to Terraform Cloud")
def _nothing_sent(api):
    api.workspaces.set_vcs_repo.assert_not_called()


@then(parsers.parse('the workspace repository should be set to "{identifier}"'))
def _set(api, identifier):
    api.workspaces.set_vcs_repo.assert_called_once()
    assert api.workspaces.set_vcs_repo.call_args.args[:2] == ("my-app-dev", identifier)


@then(parsers.parse('I should see error message containing "{text}"'))
def _err(result, text):
    assert text in result.output


@then(parsers.parse("exit code should be {code:d}"))
def _code(result, code):
    assert result.exit_code == code, result.output
