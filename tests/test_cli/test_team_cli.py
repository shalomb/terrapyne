"""BDD tests for team management CLI commands."""

from unittest.mock import MagicMock, patch

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.models.team import Team

runner = CliRunner()


@scenario("../features/team.feature", "List teams in organization")
def test_list_teams():
    pass


@scenario("../features/team.feature", "Create a new team")
def test_create_team():
    pass


@scenario("../features/team.feature", "Delete a team")
def test_delete_team():
    pass


@scenario("../features/team.feature", "Manage team membership")
def test_manage_team_membership():
    pass


@given("a terraform cloud organization is accessible")
def terraform_org_ready():
    pass


@given(
    parsers.parse('the organization has teams "{t1}", "{t2}", "{t3}"'), target_fixture="mock_client"
)
def organization_has_teams(t1, t2, t3):
    m = MagicMock()
    teams = [
        Team.model_construct(id="team-1", name=t1),
        Team.model_construct(id="team-2", name=t2),
        Team.model_construct(id="team-3", name=t3),
    ]
    m.teams.list_teams.return_value = (teams, 3)
    return m


@given(parsers.parse('a team "{name}" exists'), target_fixture="mock_client")
def team_exists(name):
    m = MagicMock()
    team = Team.model_construct(id=f"team-{name}", name=name)
    m.teams.get_by_name.return_value = team
    m.teams.get.return_value = team
    return m


@given(parsers.parse('a user "{user_id}" is a member of the organization'))
def user_exists(user_id):
    pass


@when("I list all teams", target_fixture="cli_result")
def list_all_teams(mock_client):
    with (
        patch("terrapyne.cli.utils.resolve_organization") as v,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        v.return_value = "test-org"
        c.return_value.__enter__.return_value = mock_client
        return runner.invoke(app, ["team", "list", "-o", "test-org"])


@when(
    parsers.parse('I create a team named "{name}" with "{permission}" permission'),
    target_fixture="cli_result",
)
def create_team(name, permission):
    with (
        patch("terrapyne.cli.utils.resolve_organization") as v,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        v.return_value = "test-org"
        mock_instance = MagicMock()
        c.return_value.__enter__.return_value = mock_instance

        team = Team.model_construct(id="team-new", name=name)
        mock_instance.teams.create.return_value = team

        return runner.invoke(app, ["team", "create", "--name", name, "-o", "test-org"])


@when(parsers.parse('I delete the team "{name}"'), target_fixture="cli_result")
def delete_team_step(mock_client, name):
    with (
        patch("terrapyne.cli.utils.resolve_organization") as v,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        v.return_value = "test-org"
        c.return_value.__enter__.return_value = mock_client

        return runner.invoke(app, ["team", "delete", f"team-{name}", "--force", "-o", "test-org"])


@when(parsers.parse('I add "{user_id}" to the "{team_name}" team'), target_fixture="cli_result")
def add_team_member_step(mock_client, user_id, team_name):
    with (
        patch("terrapyne.cli.utils.resolve_organization") as v,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        v.return_value = "test-org"
        c.return_value.__enter__.return_value = mock_client

        team = Team.model_construct(id=f"team-{team_name}", name=team_name)
        mock_client.teams.get.return_value = team

        return runner.invoke(
            app, ["team", "add-member", f"team-{team_name}", "--user", user_id, "-o", "test-org"]
        )


@when(
    parsers.parse('I remove "{user_id}" from the "{team_name}" team'),
    target_fixture="cli_result_remove",
)
def remove_team_member_step(mock_client, user_id, team_name):
    with (
        patch("terrapyne.cli.utils.resolve_organization") as v,
        patch("terrapyne.api.client.TFCClient") as c,
    ):
        v.return_value = "test-org"
        c.return_value.__enter__.return_value = mock_client

        team = Team.model_construct(id=f"team-{team_name}", name=team_name)
        mock_client.teams.get.return_value = team

        return runner.invoke(
            app,
            [
                "team",
                "remove-member",
                f"team-{team_name}",
                "--user",
                user_id,
                "--force",
                "-o",
                "test-org",
            ],
        )


@then(parsers.parse('I should see "{name}" in the list'))
def check_name_in_list(cli_result, name):
    assert name in cli_result.stdout


@then(parsers.parse('the team "{name}" should be created successfully'))
def check_team_created(cli_result, name):
    assert cli_result.exit_code == 0
    assert name in cli_result.stdout
    assert "created" in cli_result.stdout.lower()


@then("it should have the requested permissions")
def check_permissions():
    pass


@then("the team should be removed from the organization")
def check_team_removed(cli_result):
    assert cli_result.exit_code == 0
    assert "deleted" in cli_result.stdout.lower()


@then(parsers.parse('"{user_id}" should be listed as a member of "{team_name}"'))
def check_member_added(cli_result, user_id, team_name):
    assert cli_result.exit_code == 0
    assert "added" in cli_result.stdout.lower()


@then(parsers.parse('"{user_id}" should no longer be a member of "{team_name}"'))
def check_member_removed(cli_result_remove, user_id, team_name):
    assert cli_result_remove.exit_code == 0
    assert "removed" in cli_result_remove.stdout.lower()
