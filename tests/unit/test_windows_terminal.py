"""Unit tests for windows_terminal.py."""

import json
import pytest
from pathlib import Path

from wt_tmux_picker.windows_terminal import (
    _default_settings_path,
    add_profile,
    list_tmux_profiles,
    load_settings,
    remove_tmux_profiles,
    save_settings,
)


def _write_settings(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _base_settings() -> dict:
    return {"profiles": {"list": []}}


class TestDefaultSettingsPath:
    def test_returns_path_ending_in_settings_json(self):
        result = _default_settings_path()
        assert result.name == "settings.json"


class TestLoadSettings:
    def test_loads_valid_json(self, tmp_path):
        p = tmp_path / "settings.json"
        data = {"profiles": {"list": []}}
        _write_settings(p, data)
        assert load_settings(p) == data

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_settings(tmp_path / "missing.json")

    def test_malformed_json_raises(self, tmp_path):
        p = tmp_path / "settings.json"
        p.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_settings(p)


class TestSaveSettings:
    def test_writes_json_to_disk(self, tmp_path):
        p = tmp_path / "settings.json"
        data = {"profiles": {"list": [{"name": "foo"}]}}
        p.write_text("{}", encoding="utf-8")
        save_settings(data, p)
        assert json.loads(p.read_text(encoding="utf-8")) == data


class TestAddProfile:
    def test_adds_profile(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, _base_settings())
        added = add_profile("myhost", settings_path=p)
        assert added is True
        settings = load_settings(p)
        names = [pr["name"] for pr in settings["profiles"]["list"]]
        assert "myhost tmux" in names

    def test_duplicate_profile_skipped(self, tmp_path):
        p = tmp_path / "settings.json"
        data = _base_settings()
        data["profiles"]["list"].append({"name": "myhost tmux"})
        _write_settings(p, data)
        added = add_profile("myhost", settings_path=p)
        assert added is False

    def test_profile_commandline_contains_host(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, _base_settings())
        add_profile("myhost", settings_path=p)
        settings = load_settings(p)
        profile = settings["profiles"]["list"][0]
        assert "myhost" in profile["commandline"]
        assert "wt-tmux-picker attach" in profile["commandline"]

    def test_profile_commandline_with_user(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, _base_settings())
        add_profile("myhost", user="alice", settings_path=p)
        settings = load_settings(p)
        profile = settings["profiles"]["list"][0]
        assert "--user alice" in profile["commandline"]

    def test_dry_run_does_not_write(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, _base_settings())
        add_profile("myhost", settings_path=p, dry_run=True)
        settings = load_settings(p)
        assert settings["profiles"]["list"] == []

    def test_settings_without_profiles_key(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, {})
        added = add_profile("myhost", settings_path=p)
        assert added is True


class TestListTmuxProfiles:
    def test_returns_tmux_profile_names(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, {
            "profiles": {"list": [
                {"name": "devbox tmux"},
                {"name": "PowerShell"},
                {"name": "prod tmux"},
            ]}
        })
        result = list_tmux_profiles(settings_path=p)
        assert result == ["devbox tmux", "prod tmux"]

    def test_returns_empty_when_none_registered(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, {"profiles": {"list": [{"name": "PowerShell"}]}})
        assert list_tmux_profiles(settings_path=p) == []

    def test_returns_empty_when_file_missing(self, tmp_path):
        assert list_tmux_profiles(settings_path=tmp_path / "missing.json") == []


class TestRemoveTmuxProfiles:
    def test_removes_all_tmux_profiles(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, {
            "profiles": {"list": [
                {"name": "myhost tmux"},
                {"name": "PowerShell"},
            ]}
        })
        removed = remove_tmux_profiles(settings_path=p)
        assert removed == ["myhost tmux"]
        settings = load_settings(p)
        assert len(settings["profiles"]["list"]) == 1
        assert settings["profiles"]["list"][0]["name"] == "PowerShell"

    def test_removes_specific_hosts(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, {
            "profiles": {"list": [
                {"name": "devbox tmux"},
                {"name": "prod tmux"},
                {"name": "PowerShell"},
            ]}
        })
        removed = remove_tmux_profiles(["devbox tmux"], settings_path=p)
        assert removed == ["devbox tmux"]
        settings = load_settings(p)
        names = [pr["name"] for pr in settings["profiles"]["list"]]
        assert "devbox tmux" not in names
        assert "prod tmux" in names

    def test_nothing_to_remove(self, tmp_path):
        p = tmp_path / "settings.json"
        _write_settings(p, {"profiles": {"list": [{"name": "PowerShell"}]}})
        removed = remove_tmux_profiles(settings_path=p)
        assert removed == []

    def test_dry_run_does_not_write(self, tmp_path):
        p = tmp_path / "settings.json"
        data = {"profiles": {"list": [{"name": "myhost tmux"}]}}
        _write_settings(p, data)
        removed = remove_tmux_profiles(settings_path=p, dry_run=True)
        assert removed == ["myhost tmux"]
        settings = load_settings(p)
        assert len(settings["profiles"]["list"]) == 1

    def test_missing_settings_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            remove_tmux_profiles(settings_path=tmp_path / "missing.json")
