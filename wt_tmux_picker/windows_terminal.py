"""Read and write Windows Terminal settings.json."""

from __future__ import annotations

import json
import re
import sys
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


def _strip_comments(text: str) -> str:
    """Remove ``//`` line comments and ``/* */`` block comments.

    The parser tracks string boundaries so that comment-like tokens
    inside quoted values are never modified.
    """
    result: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            result.append(c)
            i += 1
            while i < n:
                sc = text[i]
                result.append(sc)
                if sc == '\\':
                    i += 1
                    if i < n:
                        result.append(text[i])
                elif sc == '"':
                    break
                i += 1
            i += 1
        elif c == '/' and i + 1 < n and text[i + 1] == '/':
            i += 2
            while i < n and text[i] != '\n':
                i += 1
        elif c == '/' and i + 1 < n and text[i + 1] == '*':
            i += 2
            while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
        else:
            result.append(c)
            i += 1
    return ''.join(result)


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before ``]`` or ``}``.

    Respects string boundaries so commas inside quoted values are
    never modified.
    """
    result: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            result.append(c)
            i += 1
            while i < n:
                sc = text[i]
                result.append(sc)
                if sc == '\\':
                    i += 1
                    if i < n:
                        result.append(text[i])
                elif sc == '"':
                    break
                i += 1
            i += 1
        elif c == ',':
            j = i + 1
            while j < n and text[j] in ' \t\r\n':
                j += 1
            if j < n and text[j] in ']}':
                i = j
            else:
                result.append(c)
                i += 1
        else:
            result.append(c)
            i += 1
    return ''.join(result)


def _strip_jsonc(text: str) -> str:
    """Remove comments and trailing commas from JSONC text.

    Uses a two-pass approach: first strips all comments, then strips
    trailing commas from the comment-free result. This correctly
    handles cases where a comment sits between a trailing comma and
    a closing bracket.
    """
    return _strip_trailing_commas(_strip_comments(text))


def _has_jsonc_comments(text: str) -> bool:
    """Return True if *text* contains ``//`` or ``/* */`` outside strings."""
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n:
                sc = text[i]
                if sc == '\\':
                    i += 2
                    continue
                if sc == '"':
                    break
                i += 1
            i += 1
        elif c == '/' and i + 1 < n and text[i + 1] in '/*':
            return True
        else:
            i += 1
    return False


def load_settings(path: Path | None = None) -> dict:
    """Read and parse settings.json.

    Handles JSONC features (comments and trailing commas) used by
    Windows Terminal.

    Raises FileNotFoundError if the file does not exist.
    Raises json.JSONDecodeError if the file is not valid JSON.
    """
    p = path or _default_settings_path()
    text = p.read_text(encoding="utf-8-sig")
    return json.loads(_strip_jsonc(text))


def save_settings(
    settings: dict, path: Path | None = None, *, _warn: bool = True
) -> None:
    """Write *settings* back to disk as pretty-printed UTF-8 JSON.

    JSONC comments present in the original file are not preserved.
    """
    p = path or _default_settings_path()
    if _warn:
        try:
            original = p.read_text(encoding="utf-8-sig")
            if _has_jsonc_comments(original):
                print(
                    "WARNING: comments in settings.json will not be preserved.",
                    file=sys.stderr,
                )
        except FileNotFoundError:
            pass
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
