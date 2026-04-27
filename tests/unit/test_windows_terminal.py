"""Unit tests for windows_terminal.py."""

import json
import pytest
from pathlib import Path

from wt_tmux_picker.windows_terminal import (
    _default_settings_path,
    _strip_jsonc,
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

    def test_loads_json_with_utf8_bom(self, tmp_path):
        p = tmp_path / "settings.json"
        data = {"profiles": {"list": []}}
        p.write_bytes(b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8"))
        assert load_settings(p) == data

    def test_loads_jsonc_with_line_comments(self, tmp_path):
        p = tmp_path / "settings.json"
        p.write_text(
            '{\n// comment\n"profiles": {"list": []}\n}',
            encoding="utf-8",
        )
        assert load_settings(p) == {"profiles": {"list": []}}

    def test_loads_jsonc_with_block_comments(self, tmp_path):
        p = tmp_path / "settings.json"
        p.write_text(
            '{/* block */"profiles": {"list": []}}',
            encoding="utf-8",
        )
        assert load_settings(p) == {"profiles": {"list": []}}

    def test_loads_jsonc_with_trailing_comma(self, tmp_path):
        p = tmp_path / "settings.json"
        p.write_text(
            '{"profiles": {"list": [{"name": "a"},]}}',
            encoding="utf-8",
        )
        result = load_settings(p)
        assert result["profiles"]["list"] == [{"name": "a"}]


class TestStripJsonc:
    def test_preserves_slashes_in_strings(self):
        text = '{"url": "https://example.com"}'
        assert json.loads(_strip_jsonc(text)) == {"url": "https://example.com"}

    def test_handles_escaped_quotes_in_strings(self):
        text = '{"val": "a \\\"b\\\""}'
        assert _strip_jsonc(text) == text

    def test_strips_line_comment_after_value(self):
        text = '{"a": 1 // comment\n}'
        assert json.loads(_strip_jsonc(text)) == {"a": 1}

    def test_strips_block_comment_inline(self):
        text = '{"a": /* x */ 1}'
        assert json.loads(_strip_jsonc(text)) == {"a": 1}

    def test_removes_trailing_comma_in_array(self):
        text = '[1, 2,]'
        assert json.loads(_strip_jsonc(text)) == [1, 2]

    def test_removes_trailing_comma_in_object(self):
        text = '{"a": 1,}'
        assert json.loads(_strip_jsonc(text)) == {"a": 1}

    def test_empty_input(self):
        assert _strip_jsonc("") == ""

    def test_backslash_at_end_of_string(self):
        text = '"a\\'
        assert _strip_jsonc(text) == '"a\\'

    def test_unterminated_string(self):
        text = '"abc'
        assert _strip_jsonc(text) == '"abc'


class TestSaveSettings:
    def test_writes_json_to_disk(self, tmp_path):
        p = tmp_path / "settings.json"
        data = {"profiles": {"list": [{"name": "foo"}]}}
        p.write_text("{}", encoding="utf-8")
        save_settings(data, p)
        assert json.loads(p.read_text(encoding="utf-8")) == data

    def test_warns_when_comments_present(self, tmp_path, capsys):
        p = tmp_path / "settings.json"
        p.write_text('{// comment\n}', encoding="utf-8")
        save_settings({"a": 1}, p)
        assert "WARNING" in capsys.readouterr().err

    def test_no_warning_without_comments(self, tmp_path, capsys):
        p = tmp_path / "settings.json"
        p.write_text('{}', encoding="utf-8")
        save_settings({"a": 1}, p)
        assert capsys.readouterr().err == ""

    def test_no_warning_when_file_missing(self, tmp_path, capsys):
        p = tmp_path / "settings.json"
        save_settings({"a": 1}, p)
        assert capsys.readouterr().err == ""

    def test_warn_false_suppresses_warning(self, tmp_path, capsys):
        p = tmp_path / "settings.json"
        p.write_text('{// comment\n}', encoding="utf-8")
        save_settings({"a": 1}, p, _warn=False)
        assert capsys.readouterr().err == ""


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
