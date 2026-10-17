"""BDD step definitions for configuration profiles."""

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.cli.main import app
from terrapyne.core.config import find_config_file, load_config
from terrapyne.core.context import resolve_organization

scenarios("../features/profiles.feature")

runner = CliRunner()


@pytest.fixture
def profile_test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home_dir = tmp_path / "fake_home"
    home_dir.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    xdg_dir = tmp_path / "fake_xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))

    # Clear environment overrides
    monkeypatch.delenv("TFC_ORG", raising=False)
    monkeypatch.delenv("TERRAPYNE_PROFILE", raising=False)
    monkeypatch.delenv("TFC_PROFILE", raising=False)

    return {
        "tmp_path": tmp_path,
        "home_dir": home_dir,
        "xdg_dir": xdg_dir,
        "resolved_path": None,
        "cli_result": None,
        "work_dir": tmp_path / "repo",
    }


@given(
    parsers.parse(
        'a configuration file ".terrapyne.toml" exists in the repository root with profile "{profile_name}"'
    )
)
def _cfg_in_repo_root(profile_test_env, profile_name):
    repo_dir = profile_test_env["work_dir"]
    repo_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = repo_dir / ".terrapyne.toml"
    cfg_file.write_text(
        f"""
current_profile = "{profile_name}"

[profiles.{profile_name}]
organization = "{profile_name}"
hostname = "app.terraform.io"
"""
    )
    profile_test_env["root_cfg"] = cfg_file


@given("the current working directory is a deep subfolder inside the repository")
def _deep_subfolder(profile_test_env, monkeypatch: pytest.MonkeyPatch):
    deep_dir = profile_test_env["work_dir"] / "packages" / "infra" / "submodules"
    deep_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(deep_dir)
    profile_test_env["deep_dir"] = deep_dir


@when("I inspect the resolved configuration path")
def _inspect_config_path(profile_test_env):
    profile_test_env["resolved_path"] = find_config_file(profile_test_env["deep_dir"])


@then('the resolved path points to the root ".terrapyne.toml"')
def _check_resolved_path(profile_test_env):
    assert profile_test_env["resolved_path"] == profile_test_env["root_cfg"]


@then(parsers.parse('the active organization is resolved as "{expected_org}"'))
def _check_resolved_org(profile_test_env, expected_org):
    resolved = resolve_organization(None)
    assert resolved == expected_org


@given('no ".terrapyne.toml" file exists in the directory hierarchy')
def _no_local_config(profile_test_env, monkeypatch: pytest.MonkeyPatch):
    empty_repo = profile_test_env["tmp_path"] / "empty_repo"
    empty_repo.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(empty_repo)


@given(
    parsers.parse(
        'an XDG configuration file exists with profile "{profile_name}" for organization "{org}"'
    )
)
def _xdg_config_exists(profile_test_env, profile_name, org):
    xdg_file = profile_test_env["xdg_dir"] / "terrapyne" / "config.toml"
    xdg_file.parent.mkdir(parents=True, exist_ok=True)
    xdg_file.write_text(
        f"""
current_profile = "{profile_name}"

[profiles.{profile_name}]
organization = "{org}"
hostname = "app.terraform.io"
"""
    )
    profile_test_env["xdg_file"] = xdg_file


@when("I run a command without specifying an organization")
def _run_without_org(profile_test_env):
    # Testing that context resolution succeeds without specifying organization
    pass


@given('an XDG configuration file contains profiles "staging" and "production"')
def _xdg_multiple_profiles(profile_test_env):
    xdg_file = profile_test_env["xdg_dir"] / "terrapyne" / "config.toml"
    xdg_file.parent.mkdir(parents=True, exist_ok=True)
    xdg_file.write_text(
        """
current_profile = "production"

[profiles.staging]
organization = "Acme-Staging"
hostname = "app.terraform.io"

[profiles.production]
organization = "Acme-Prod"
hostname = "app.terraform.io"
"""
    )
    profile_test_env["xdg_file"] = xdg_file


@when(parsers.parse('I run "{command}"'))
def _run_cli_command(profile_test_env, command):
    args = command.split()[1:]  # strip 'tfc'
    res = runner.invoke(app, args)
    profile_test_env["cli_result"] = res


@then(parsers.parse('the profile details for "{name}" are displayed'))
def _check_profile_show_output(profile_test_env, name):
    res = profile_test_env["cli_result"]
    assert res.exit_code == 0
    assert name in res.output


@given('a configuration file contains profiles "dev" and "prod"')
def _cfg_contains_dev_and_prod(profile_test_env):
    xdg_file = profile_test_env["xdg_dir"] / "terrapyne" / "config.toml"
    xdg_file.parent.mkdir(parents=True, exist_ok=True)
    xdg_file.write_text(
        """
current_profile = "dev"

[profiles.dev]
organization = "Org-Dev"

[profiles.prod]
organization = "Org-Prod"
"""
    )
    profile_test_env["xdg_file"] = xdg_file


@then("the command succeeds")
def _command_succeeds(profile_test_env):
    res = profile_test_env["cli_result"]
    assert res.exit_code == 0, f"Command failed: {res.output}"


@then(parsers.parse('the current profile is saved as "{expected_profile}"'))
def _check_current_profile_saved(profile_test_env, expected_profile):
    cfg = load_config(path=profile_test_env["xdg_file"])
    assert cfg.current_profile == expected_profile
