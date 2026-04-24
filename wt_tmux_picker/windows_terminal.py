"""Read and write Windows Terminal settings.json."""

from __future__ import annotations

import json
import uuid
from pathlib import Path


_WT_SETTINGS_PATH = (
    Path.home()
    / "AppData"
    / "Local"
    / "Packages"
    / "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
    / "LocalState"
    / "settings.json"
)


def _default_settings_path() -> Path:
    return _WT_SETTINGS_PATH


def load_settings(path: Path | None = None) -> dict:
    """Read and parse settings.json.

    Raises FileNotFoundError if the file does not exist.
    Raises json.JSONDecodeError if the file is not valid JSON.
    """
    p = path or _default_settings_path()
    text = p.read_text(encoding="utf-8")
    return json.loads(text)


def save_settings(settings: dict, path: Path | None = None) -> None:
    """Write *settings* back to disk as pretty-printed UTF-8 JSON."""
    p = path or _default_settings_path()
    p.write_text(json.dumps(settings, indent=4), encoding="utf-8")


def _profile_name(host: str) -> str:
    return f"{host} tmux"


def add_profile(
    host: str,
    user: str | None = None,
    *,
    settings_path: Path | None = None,
    dry_run: bool = False,
) -> bool:
    """Add a Windows Terminal profile for *host*.

    Returns True if the profile was added, False if it already existed.
    In dry-run mode the file is not written.
    """
    settings = load_settings(settings_path)
    profiles: list[dict] = settings.setdefault("profiles", {}).setdefault("list", [])

    name = _profile_name(host)
    if any(p.get("name") == name for p in profiles):
        return False

    target = f"--user {user} {host}" if user else host
    profile = {
        "guid": "{" + str(uuid.uuid5(uuid.NAMESPACE_DNS, host)) + "}",
        "name": name,
        "commandline": f"wt-tmux-picker attach {target}",
        "hidden": False,
    }
    profiles.append(profile)

    if not dry_run:
        save_settings(settings, settings_path)
    return True


def list_tmux_profiles(*, settings_path: Path | None = None) -> list[str]:
    """Return names of all registered ' tmux' profiles."""
    try:
        settings = load_settings(settings_path)
    except FileNotFoundError:
        return []
    profiles: list[dict] = settings.get("profiles", {}).get("list", [])
    return [p["name"] for p in profiles if p.get("name", "").endswith(" tmux")]


def remove_tmux_profiles(
    hosts: list[str] | None = None,
    *,
    settings_path: Path | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Remove ' tmux' profiles from Windows Terminal settings.

    If *hosts* is given, only profiles whose names are in *hosts* are removed.
    If *hosts* is None, all profiles ending with ' tmux' are removed.
    Returns the list of removed profile names.
    In dry-run mode the file is not written.
    """
    settings = load_settings(settings_path)
    profiles: list[dict] = settings.get("profiles", {}).get("list", [])

    removed: list[str] = []
    kept: list[dict] = []
    for p in profiles:
        name = p.get("name", "")
        should_remove = (hosts is None and name.endswith(" tmux")) or (
            hosts is not None and name in hosts
        )
        if should_remove:
            removed.append(name)
        else:
            kept.append(p)

    if removed and not dry_run:
        settings["profiles"]["list"] = kept
        save_settings(settings, settings_path)

    return removed
