"""Functional tests for the full cleanup flow."""

import json
from pathlib import Path
from unittest.mock import patch

from wt_tmux_picker.cli import _cleanup


def _make_wt_settings(tmp_path: Path, profiles: list[dict] | None = None) -> Path:
    p = tmp_path / "settings.json"
    data = {"profiles": {"list": profiles or []}}
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


class TestCleanupFlow:
    def test_removes_all_via_tui(self, tmp_path):
        wt = _make_wt_settings(tmp_path, [
            {"name": "alpha tmux"},
            {"name": "beta tmux"},
            {"name": "PowerShell"},
        ])

        with patch(
            "wt_tmux_picker.cli.pick_profiles",
            return_value=["alpha tmux", "beta tmux"],
        ):
            rc = _cleanup(dry_run=False, settings_path=wt)

        assert rc == 0
        settings = json.loads(wt.read_text(encoding="utf-8"))
        names = [p["name"] for p in settings["profiles"]["list"]]
        assert "alpha tmux" not in names
        assert "beta tmux" not in names
        assert "PowerShell" in names

    def test_removes_specific_hosts(self, tmp_path):
        wt = _make_wt_settings(tmp_path, [
            {"name": "alpha tmux"},
            {"name": "beta tmux"},
        ])

        rc = _cleanup(dry_run=False, hosts=["alpha"], settings_path=wt)

        assert rc == 0
        settings = json.loads(wt.read_text(encoding="utf-8"))
        names = [p["name"] for p in settings["profiles"]["list"]]
        assert "alpha tmux" not in names
        assert "beta tmux" in names

    def test_dry_run_preserves_settings(self, tmp_path):
        wt = _make_wt_settings(tmp_path, [{"name": "alpha tmux"}])
        original = wt.read_text(encoding="utf-8")

        _cleanup(dry_run=True, hosts=["alpha"], settings_path=wt)

        assert wt.read_text(encoding="utf-8") == original

    def test_idempotent_second_cleanup(self, tmp_path):
        wt = _make_wt_settings(tmp_path, [{"name": "alpha tmux"}])

        with patch("wt_tmux_picker.cli.pick_profiles", return_value=["alpha tmux"]):
            _cleanup(dry_run=False, settings_path=wt)

        rc = _cleanup(dry_run=False, hosts=["alpha"], settings_path=wt)
        assert rc == 0
