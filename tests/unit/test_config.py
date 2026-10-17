"""Unit tests for configuration and profile management."""

from pathlib import Path

import pytest

from terrapyne.core.config import (
    Profile,
    TerrapyneConfig,
    find_config_file,
    load_config,
)
from terrapyne.core.context import resolve_host, resolve_organization, resolve_workspace


class TestConfigDiscovery:
    """Test locating .terrapyne.toml up the directory hierarchy and XDG fallback."""

    def test_finds_in_current_directory(self, tmp_path: Path):
        cfg_file = tmp_path / ".terrapyne.toml"
        cfg_file.write_text('current_profile = "local"\n')

        found = find_config_file(start_dir=tmp_path)
        assert found == cfg_file

    def test_finds_in_parent_directory(self, tmp_path: Path):
        parent_dir = tmp_path / "workspace"
        child_dir = parent_dir / "subdir" / "deep"
        child_dir.mkdir(parents=True)

        cfg_file = parent_dir / ".terrapyne.toml"
        cfg_file.write_text('current_profile = "parent"\n')

        found = find_config_file(start_dir=child_dir)
        assert found == cfg_file

    def test_stops_at_home_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        home_dir = tmp_path / "home" / "user"
        outside_dir = tmp_path / "other"
        home_dir.mkdir(parents=True)
        outside_dir.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: home_dir)

        # File in directory above home should not be found if searching inside home
        above_home = tmp_path / "home" / ".terrapyne.toml"
        above_home.write_text('current_profile = "above"\n')

        found = find_config_file(start_dir=home_dir)
        assert found is None

    def test_falls_back_to_xdg_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        home_dir = tmp_path / "home" / "user"
        home_dir.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        xdg_config_home = tmp_path / "custom_xdg"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config_home))

        xdg_cfg_file = xdg_config_home / "terrapyne" / "config.toml"
        xdg_cfg_file.parent.mkdir(parents=True)
        xdg_cfg_file.write_text('current_profile = "xdg"\n')

        # Run from an empty directory
        workdir = tmp_path / "project"
        workdir.mkdir()
        found = find_config_file(start_dir=workdir)
        assert found == xdg_cfg_file

    def test_returns_none_when_no_config_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        empty_home = tmp_path / "empty_home"
        empty_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: empty_home)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nonexistent_xdg"))

        found = find_config_file(start_dir=empty_dir)
        assert found is None


class TestConfigLoadingAndSaving:
    """Test parsing and serialization of TerrapyneConfig and Profile."""

    def test_load_config_from_toml(self, tmp_path: Path):
        cfg_file = tmp_path / ".terrapyne.toml"
        cfg_file.write_text(
            """
current_profile = "takeda"

[profiles.default]
organization = "personal"
hostname = "app.terraform.io"

[profiles.takeda]
organization = "Takeda"
hostname = "app.terraform.io"
default_project = "Infrastructure-Core"
default_workspace = "network-prod"
poll_timeout = 600
format = "json"
"""
        )

        cfg = load_config(path=cfg_file)
        assert cfg.current_profile == "takeda"
        assert len(cfg.profiles) == 2
        assert cfg.source_path == cfg_file

        profile = cfg.get_profile()
        assert profile is not None
        assert profile.name == "takeda"
        assert profile.organization == "Takeda"
        assert profile.default_project == "Infrastructure-Core"
        assert profile.poll_timeout == 600
        assert profile.format == "json"

    def test_get_profile_by_name_and_fallback(self):
        cfg = TerrapyneConfig(
            current_profile="prod",
            profiles={
                "prod": Profile(name="prod", organization="ProdOrg"),
                "staging": Profile(name="staging", organization="StagingOrg"),
                "default": Profile(name="default", organization="DefaultOrg"),
            },
        )

        assert cfg.get_profile("staging").organization == "StagingOrg"
        assert cfg.get_profile().organization == "ProdOrg"

        # If current_profile is unset, fallback to "default"
        cfg.current_profile = None
        assert cfg.get_profile().organization == "DefaultOrg"

    def test_save_config_updates_file(self, tmp_path: Path):
        cfg_file = tmp_path / ".terrapyne.toml"
        cfg = TerrapyneConfig(
            current_profile="dev",
            profiles={
                "dev": Profile(name="dev", organization="DevOrg", hostname="app.terraform.io"),
            },
            source_path=cfg_file,
        )
        saved_path = cfg.save()
        assert saved_path == cfg_file

        reloaded = load_config(path=cfg_file)
        assert reloaded.current_profile == "dev"
        assert reloaded.profiles["dev"].organization == "DevOrg"
        assert reloaded.profiles["dev"].hostname == "app.terraform.io"


class TestContextResolutionWithProfiles:
    """Test precedence rules for resolving organization, host, and workspace."""

    def test_resolve_organization_precedence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # 1. CLI flag wins over all
        cfg = TerrapyneConfig(
            current_profile="test",
            profiles={"test": Profile(name="test", organization="ProfileOrg")},
        )
        monkeypatch.setenv("TFC_ORG", "EnvOrg")
        assert resolve_organization("CliOrg", config=cfg) == "CliOrg"

        # 2. Env var wins over profile
        assert resolve_organization(None, config=cfg) == "EnvOrg"

        # 3. Profile wins when env var and CLI flag are absent
        monkeypatch.delenv("TFC_ORG", raising=False)
        assert resolve_organization(None, config=cfg) == "ProfileOrg"

    def test_resolve_host_precedence(self, monkeypatch: pytest.MonkeyPatch):
        cfg = TerrapyneConfig(
            current_profile="enterprise",
            profiles={"enterprise": Profile(name="enterprise", hostname="tfe.corp.internal")},
        )

        # 1. CLI flag
        assert resolve_host("tfe.custom.com", config=cfg) == "tfe.custom.com"

        # 2. Env var
        monkeypatch.setenv("TFC_HOST", "tfe.env.internal")
        assert resolve_host(None, config=cfg) == "tfe.env.internal"

        # 3. Profile
        monkeypatch.delenv("TFC_HOST", raising=False)
        assert resolve_host(None, config=cfg) == "tfe.corp.internal"

        # 4. Default fallback
        empty_cfg = TerrapyneConfig()
        assert resolve_host(None, config=empty_cfg) == "app.terraform.io"

    def test_resolve_workspace_precedence(self, monkeypatch: pytest.MonkeyPatch):
        cfg = TerrapyneConfig(
            current_profile="test",
            profiles={"test": Profile(name="test", default_workspace="profile-ws")},
        )

        # 1. CLI flag
        assert resolve_workspace("cli-ws", config=cfg) == "cli-ws"

        # 2. Env var
        monkeypatch.setenv("TFC_WORKSPACE", "env-ws")
        assert resolve_workspace(None, config=cfg) == "env-ws"

        # 3. Profile default
        monkeypatch.delenv("TFC_WORKSPACE", raising=False)
        assert resolve_workspace(None, config=cfg) == "profile-ws"
