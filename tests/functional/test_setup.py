"""Functional tests for the full setup flow."""

import json
from pathlib import Path
from unittest.mock import patch

from wt_tmux_picker.cli import _setup


def _make_ssh_config(tmp_path: Path, hosts: list[str]) -> Path:
    p = tmp_path / "ssh_config"
    p.write_text("\n".join(f"Host {h}" for h in hosts), encoding="utf-8")
    return p


def _make_wt_settings(tmp_path: Path) -> Path:
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"profiles": {"list": []}}), encoding="utf-8")
    return p


class TestSetupFlow:
    def test_full_setup_registers_profiles(self, tmp_path):
        cfg = _make_ssh_config(tmp_path, ["alpha", "beta"])
        wt = _make_wt_settings(tmp_path)

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
        ):
            rc = _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        assert rc == 0
        settings = json.loads(wt.read_text(encoding="utf-8"))
        names = {p["name"] for p in settings["profiles"]["list"]}
        assert "alpha tmux" in names
        assert "beta tmux" in names

    def test_profile_commandline_uses_attach(self, tmp_path):
        cfg = _make_ssh_config(tmp_path, ["myhost"])
        wt = _make_wt_settings(tmp_path)

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
        ):
            _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        settings = json.loads(wt.read_text(encoding="utf-8"))
        profile = settings["profiles"]["list"][0]
        assert "wt-tmux-picker attach" in profile["commandline"]
        assert "myhost" in profile["commandline"]

    def test_hosts_without_tmux_not_added(self, tmp_path):
        cfg = _make_ssh_config(tmp_path, ["good", "bad"])
        wt = _make_wt_settings(tmp_path)

        def fake_has_tmux(host, user=None, *, dry_run=False):
            return host == "good"

        with (
            patch("wt_tmux_picker.cli.has_tmux", side_effect=fake_has_tmux),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
        ):
            _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        settings = json.loads(wt.read_text(encoding="utf-8"))
        names = {p["name"] for p in settings["profiles"]["list"]}
        assert "good tmux" in names
        assert "bad tmux" not in names

    def test_hosts_without_fzf_not_added(self, tmp_path):
        cfg = _make_ssh_config(tmp_path, ["good", "bad"])
        wt = _make_wt_settings(tmp_path)

        def fake_has_fzf(host, user=None, *, dry_run=False):
            return host == "good"

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", side_effect=fake_has_fzf),
        ):
            _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        settings = json.loads(wt.read_text(encoding="utf-8"))
        names = {p["name"] for p in settings["profiles"]["list"]}
        assert "good tmux" in names
        assert "bad tmux" not in names

    def test_dry_run_leaves_settings_unchanged(self, tmp_path):
        cfg = _make_ssh_config(tmp_path, ["alpha"])
        wt = _make_wt_settings(tmp_path)
        original = wt.read_text(encoding="utf-8")

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
        ):
            _setup(user=None, ssh_config=cfg, dry_run=True, settings_path=wt)

        assert wt.read_text(encoding="utf-8") == original

    def test_user_param_in_commandline(self, tmp_path):
        cfg = _make_ssh_config(tmp_path, ["myhost"])
        wt = _make_wt_settings(tmp_path)

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
        ):
            _setup(user="alice", ssh_config=cfg, dry_run=False, settings_path=wt)

        settings = json.loads(wt.read_text(encoding="utf-8"))
        profile = settings["profiles"]["list"][0]
        assert "alice" in profile["commandline"]
