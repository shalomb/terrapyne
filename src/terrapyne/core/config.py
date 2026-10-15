"""Configuration and profile management for Terrapyne."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def get_xdg_config_path() -> Path:
    """Return the canonical XDG path for the terrapyne config file."""
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        base_dir = Path(xdg_config_home)
    else:
        base_dir = Path.home() / ".config"
    return base_dir / "terrapyne" / "config.toml"


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Find the active configuration file.

    Lookup rules:
    1. Look for .terrapyne.toml in start_dir and traverse upward parent-by-parent.
       If start_dir is under Path.home(), stop the traversal at Path.home().
       If start_dir is outside Path.home(), stop at root, then check Path.home()/.terrapyne.toml.
    2. If no .terrapyne.toml is found, check the XDG config path ($XDG_CONFIG_HOME/terrapyne/config.toml
       or ~/.config/terrapyne/config.toml).
    3. Check legacy ~/.terrapyne/config.toml.
    4. Return None if no config file exists.
    """
    curr = (start_dir or Path.cwd()).resolve()
    home = Path.home().resolve()

    is_under_home = False
    try:
        is_under_home = curr.is_relative_to(home)
    except (ValueError, AttributeError):
        pass

    while True:
        candidate = curr / ".terrapyne.toml"
        if candidate.is_file():
            return candidate

        if is_under_home and curr == home:
            break
        if curr.parent == curr:  # reached root
            break
        curr = curr.parent

    # If start_dir was outside home, check home directory specifically
    if not is_under_home:
        home_candidate = home / ".terrapyne.toml"
        if home_candidate.is_file():
            return home_candidate

    # Fallback to XDG config
    xdg_candidate = get_xdg_config_path()
    if xdg_candidate.is_file():
        return xdg_candidate

    # Fallback to ~/.terrapyne/config.toml
    dot_dir_candidate = home / ".terrapyne" / "config.toml"
    if dot_dir_candidate.is_file():
        return dot_dir_candidate

    return None


class Profile(BaseModel):
    """A named configuration profile."""

    name: str
    organization: str | None = None
    hostname: str = "app.terraform.io"
    token: str | None = None
    token_env: str | None = None
    default_project: str | None = None
    default_workspace: str | None = None
    poll_interval: float | None = None
    poll_timeout: float | None = None
    cache_ttl: int | None = None
    format: str | None = None
    runner_binary: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class TerrapyneConfig(BaseModel):
    """Root configuration containing named profiles and the active profile selection."""

    current_profile: str | None = None
    profiles: dict[str, Profile] = Field(default_factory=dict)
    source_path: Path | None = None

    def get_profile(self, name: str | None = None) -> Profile | None:
        """Resolve a profile by explicit name, environment variable, current_profile, or 'default'."""
        if name:
            return self.profiles.get(name)

        env_name = os.environ.get("TERRAPYNE_PROFILE") or os.environ.get("TFC_PROFILE")
        if env_name:
            return self.profiles.get(env_name)

        if self.current_profile and self.current_profile in self.profiles:
            return self.profiles[self.current_profile]

        return self.profiles.get("default")

    def save(self, path: Path | None = None) -> Path:
        """Save configuration to disk in TOML format."""
        target_path = path or self.source_path or get_xdg_config_path()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = _dump_toml(self)
        target_path.write_text(content)
        self.source_path = target_path
        return target_path


def _format_toml_val(val: Any) -> str:
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (int, float)):
        return str(val)
    # Default to quoted string with escaping
    escaped = str(val).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _dump_toml(config: TerrapyneConfig) -> str:
    lines: list[str] = []

    if config.current_profile:
        lines.append(f"current_profile = {_format_toml_val(config.current_profile)}")
        lines.append("")

    for name, profile in config.profiles.items():
        lines.append(f"[profiles.{name}]")
        fields = [
            ("organization", profile.organization),
            ("hostname", profile.hostname if profile.hostname != "app.terraform.io" else None),
            ("token", profile.token),
            ("token_env", profile.token_env),
            ("default_project", profile.default_project),
            ("default_workspace", profile.default_workspace),
            ("poll_interval", profile.poll_interval),
            ("poll_timeout", profile.poll_timeout),
            ("cache_ttl", profile.cache_ttl),
            ("format", profile.format),
            ("runner_binary", profile.runner_binary),
        ]
        # Always output hostname if explicitly set or if default
        if profile.hostname:
            lines.append(f"hostname = {_format_toml_val(profile.hostname)}")

        for field_name, val in fields:
            if field_name == "hostname":
                continue
            if val is not None:
                lines.append(f"{field_name} = {_format_toml_val(val)}")

        for k, v in profile.extra.items():
            if v is not None:
                lines.append(f"{k} = {_format_toml_val(v)}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def load_config(path: Path | None = None, start_dir: Path | None = None) -> TerrapyneConfig:
    """Load configuration from the specified path or by automatic discovery."""
    resolved_path = path or find_config_file(start_dir)
    if not resolved_path or not resolved_path.is_file():
        return TerrapyneConfig(source_path=None)

    try:
        data = tomllib.loads(resolved_path.read_text())
    except Exception:
        return TerrapyneConfig(source_path=resolved_path)

    current_profile = data.get("current_profile")
    raw_profiles = data.get("profiles", {})

    profiles: dict[str, Profile] = {}
    known_fields = {
        "organization",
        "hostname",
        "token",
        "token_env",
        "default_project",
        "default_workspace",
        "poll_interval",
        "poll_timeout",
        "cache_ttl",
        "format",
        "runner_binary",
    }

    if isinstance(raw_profiles, dict):
        for name, p_data in raw_profiles.items():
            if not isinstance(p_data, dict):
                continue
            attrs: dict[str, Any] = {"name": name}
            extra: dict[str, Any] = {}
            for k, v in p_data.items():
                if k in known_fields:
                    attrs[k] = v
                else:
                    extra[k] = v
            attrs["extra"] = extra
            profiles[name] = Profile(**attrs)

    return TerrapyneConfig(
        current_profile=current_profile,
        profiles=profiles,
        source_path=resolved_path,
    )
