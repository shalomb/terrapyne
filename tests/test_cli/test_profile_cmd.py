"""Unit tests for tfc profile CLI commands."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from terrapyne.cli.main import app

runner = CliRunner()


@pytest.fixture
def clean_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    fake_xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_xdg))

    monkeypatch.delenv("TFC_ORG", raising=False)
    monkeypatch.delenv("TERRAPYNE_PROFILE", raising=False)
    monkeypatch.delenv("TFC_PROFILE", raising=False)

    return {"home": fake_home, "xdg": fake_xdg}


def test_profile_list_empty(clean_env):
    res = runner.invoke(app, ["profile", "list"])
    assert res.exit_code == 0
    assert "No profiles configured" in res.output


def test_profile_list_json(clean_env):
    cfg_file = clean_env["xdg"] / "terrapyne" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(
        """
current_profile = "prod"

[profiles.prod]
organization = "Takeda"
hostname = "app.terraform.io"
default_project = "Core"
"""
    )

    res = runner.invoke(app, ["profile", "list", "--format", "json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["current_profile"] == "prod"
    assert len(data["profiles"]) == 1
    assert data["profiles"][0]["organization"] == "Takeda"
    assert data["profiles"][0]["is_active"] is True


def test_profile_list_table(clean_env):
    cfg_file = clean_env["xdg"] / "terrapyne" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(
        """
current_profile = "prod"

[profiles.prod]
organization = "Takeda"
hostname = "app.terraform.io"

[profiles.staging]
organization = "Takeda-Stage"
hostname = "app.terraform.io"
"""
    )

    res = runner.invoke(app, ["profile", "list"])
    assert res.exit_code == 0
    assert "Takeda" in res.output
    assert "Takeda-Stage" in res.output
    assert "*" in res.output


def test_profile_show_active(clean_env):
    cfg_file = clean_env["xdg"] / "terrapyne" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(
        """
current_profile = "prod"

[profiles.prod]
organization = "Takeda"
hostname = "app.terraform.io"
default_project = "Infrastructure"
default_workspace = "core-network"
token = "secret-token-123"
poll_interval = 2.5
poll_timeout = 300.0
cache_ttl = 60
format = "table"
runner_binary = "tofu"
custom_field = "custom_value"
"""
    )

    res = runner.invoke(app, ["profile", "show"])
    assert res.exit_code == 0
    assert "Takeda" in res.output
    assert "Infrastructure" in res.output
    assert "core-network" in res.output
    assert "********" in res.output  # Masked token
    assert "tofu" in res.output
    assert "custom_value" in res.output


def test_profile_show_json(clean_env):
    cfg_file = clean_env["xdg"] / "terrapyne" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(
        """
current_profile = "prod"

[profiles.prod]
organization = "Takeda"
hostname = "app.terraform.io"
"""
    )

    res = runner.invoke(app, ["profile", "show", "prod", "--format", "json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["name"] == "prod"
    assert data["organization"] == "Takeda"
    assert data["is_active"] is True


def test_profile_show_nonexistent(clean_env):
    res = runner.invoke(app, ["profile", "show", "missing"])
    assert res.exit_code == 1
    assert (
        "Profile 'missing' not found" in res.output or "Profile 'missing' not found" in res.stderr
    )


def test_profile_set_values(clean_env):
    res = runner.invoke(app, ["profile", "set", "organization", "Takeda", "--profile", "custom"])
    assert res.exit_code == 0
    assert "Updated organization = 'Takeda' in profile 'custom'" in res.output

    # Set numeric fields
    res2 = runner.invoke(app, ["profile", "set", "poll_timeout", "120", "--profile", "custom"])
    assert res2.exit_code == 0

    res3 = runner.invoke(app, ["profile", "set", "cache_ttl", "30", "--profile", "custom"])
    assert res3.exit_code == 0

    # Set invalid number
    res4 = runner.invoke(
        app, ["profile", "set", "cache_ttl", "not-a-number", "--profile", "custom"]
    )
    assert res4.exit_code == 1

    res5 = runner.invoke(
        app, ["profile", "set", "poll_timeout", "bad-float", "--profile", "custom"]
    )
    assert res5.exit_code == 1


def test_profile_path(clean_env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # When no config exists
    res = runner.invoke(app, ["profile", "path"])
    assert res.exit_code == 0
    assert "Default location:" in res.output

    # When config exists
    cfg_file = clean_env["xdg"] / "terrapyne" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text('current_profile = "test"\n')

    res2 = runner.invoke(app, ["profile", "path"])
    assert res2.exit_code == 0
    assert str(cfg_file) in res2.output
