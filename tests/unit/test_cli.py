"""Unit tests for cli.py."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wt_tmux_picker.cli import _attach, _build_parser, _cleanup, _plain_ssh, _setup, main


def _write_ssh_config(tmp_path: Path, hosts: list[str]) -> Path:
    p = tmp_path / "ssh_config"
    p.write_text("\n".join(f"Host {h}" for h in hosts), encoding="utf-8")
    return p


def _write_wt_settings(tmp_path: Path, profiles: list[dict] | None = None) -> Path:
    p = tmp_path / "settings.json"
    data = {"profiles": {"list": profiles or []}}
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


class TestBuildParser:
    def test_setup_subcommand(self):
        args = _build_parser().parse_args(["setup"])
        assert args.command == "setup"

    def test_cleanup_subcommand(self):
        args = _build_parser().parse_args(["cleanup"])
        assert args.command == "cleanup"

    def test_attach_subcommand(self):
        args = _build_parser().parse_args(["attach", "devbox"])
        assert args.command == "attach"
        assert args.host == "devbox"

    def test_setup_dry_run(self):
        args = _build_parser().parse_args(["setup", "--dry-run"])
        assert args.dry_run is True

    def test_cleanup_dry_run(self):
        args = _build_parser().parse_args(["cleanup", "--dry-run"])
        assert args.dry_run is True

    def test_setup_user(self):
        args = _build_parser().parse_args(["setup", "--user", "alice"])
        assert args.user == "alice"

    def test_cleanup_hosts(self):
        args = _build_parser().parse_args(["cleanup", "devbox", "prod"])
        assert args.hosts == ["devbox", "prod"]

    def test_cleanup_no_hosts(self):
        args = _build_parser().parse_args(["cleanup"])
        assert args.hosts == []

    def test_no_subcommand_exits(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args([])


class TestSetupFunction:
    def test_happy_path_adds_profile(self, tmp_path):
        cfg = _write_ssh_config(tmp_path, ["host1"])
        wt = _write_wt_settings(tmp_path)

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
            patch("wt_tmux_picker.cli.pick_hosts", return_value=["host1"]),
        ):
            rc = _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        assert rc == 0
        settings = json.loads(wt.read_text(encoding="utf-8"))
        names = [p["name"] for p in settings["profiles"]["list"]]
        assert "host1 tmux" in names

    def test_missing_ssh_config_returns_1(self, tmp_path):
        rc = _setup(user=None, ssh_config=tmp_path / "missing", dry_run=False)
        assert rc == 1

    def test_no_hosts_returns_0(self, tmp_path, capsys):
        cfg = _write_ssh_config(tmp_path, [])
        rc = _setup(user=None, ssh_config=cfg, dry_run=False)
        assert rc == 0
        assert "No hosts" in capsys.readouterr().out

    def test_host_without_tmux_passed_as_unavailable(self, tmp_path):
        cfg = _write_ssh_config(tmp_path, ["host1"])
        wt = _write_wt_settings(tmp_path)

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=False),
            patch("wt_tmux_picker.cli.pick_hosts", return_value=[]) as mock_pick,
        ):
            _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        mock_pick.assert_called_once_with([], [("host1", "tmux not found")])

    def test_host_without_fzf_passed_as_unavailable(self, tmp_path):
        cfg = _write_ssh_config(tmp_path, ["host1"])
        wt = _write_wt_settings(tmp_path)

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=False),
            patch("wt_tmux_picker.cli.pick_hosts", return_value=[]) as mock_pick,
        ):
            _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        mock_pick.assert_called_once_with([], [("host1", "fzf not found")])

    def test_mixed_eligible_and_unavailable(self, tmp_path):
        cfg = _write_ssh_config(tmp_path, ["good", "bad"])
        wt = _write_wt_settings(tmp_path)

        def fake_has_tmux(host, user=None, *, dry_run=False):
            return host == "good"

        with (
            patch("wt_tmux_picker.cli.has_tmux", side_effect=fake_has_tmux),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
            patch("wt_tmux_picker.cli.pick_hosts", return_value=["good"]) as mock_pick,
        ):
            _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        mock_pick.assert_called_once_with(["good"], [("bad", "tmux not found")])

    def test_dry_run_prints_would_add(self, tmp_path, capsys):
        cfg = _write_ssh_config(tmp_path, ["host1"])
        wt = _write_wt_settings(tmp_path)

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
            patch("wt_tmux_picker.cli.pick_hosts", return_value=["host1"]),
        ):
            _setup(user=None, ssh_config=cfg, dry_run=True, settings_path=wt)

        out = capsys.readouterr().out
        assert "dry-run" in out
        settings = json.loads(wt.read_text(encoding="utf-8"))
        assert settings["profiles"]["list"] == []

    def test_duplicate_profile_prints_skipped(self, tmp_path, capsys):
        cfg = _write_ssh_config(tmp_path, ["host1"])
        wt = _write_wt_settings(tmp_path, [{"name": "host1 tmux"}])

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
            patch("wt_tmux_picker.cli.pick_hosts", return_value=["host1"]),
        ):
            _setup(user=None, ssh_config=cfg, dry_run=False, settings_path=wt)

        assert "already exists" in capsys.readouterr().out

    def test_no_hosts_selected_returns_0(self, tmp_path, capsys):
        cfg = _write_ssh_config(tmp_path, ["host1"])

        with (
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
            patch("wt_tmux_picker.cli.pick_hosts", return_value=[]),
        ):
            rc = _setup(user=None, ssh_config=cfg, dry_run=False)

        assert rc == 0
        assert "No hosts selected" in capsys.readouterr().out


class TestCleanupFunction:
    def test_specific_hosts_removed(self, tmp_path, capsys):
        wt = _write_wt_settings(tmp_path, [
            {"name": "devbox tmux"},
            {"name": "prod tmux"},
        ])
        rc = _cleanup(dry_run=False, hosts=["devbox"], settings_path=wt)
        assert rc == 0
        settings = json.loads(wt.read_text(encoding="utf-8"))
        names = [p["name"] for p in settings["profiles"]["list"]]
        assert "devbox tmux" not in names
        assert "prod tmux" in names
        assert "Removed" in capsys.readouterr().out

    def test_dry_run_with_hosts(self, tmp_path, capsys):
        wt = _write_wt_settings(tmp_path, [{"name": "devbox tmux"}])
        _cleanup(dry_run=True, hosts=["devbox"], settings_path=wt)
        out = capsys.readouterr().out
        assert "dry-run" in out
        settings = json.loads(wt.read_text(encoding="utf-8"))
        assert len(settings["profiles"]["list"]) == 1

    def test_no_registered_profiles_prints_nothing(self, tmp_path, capsys):
        wt = _write_wt_settings(tmp_path)
        rc = _cleanup(dry_run=False, settings_path=wt)
        assert rc == 0
        assert "Nothing to clean up" in capsys.readouterr().out

    def test_no_hosts_shows_tui_and_removes_selection(self, tmp_path, capsys):
        wt = _write_wt_settings(tmp_path, [
            {"name": "devbox tmux"},
            {"name": "prod tmux"},
        ])
        with patch("wt_tmux_picker.cli.pick_profiles", return_value=["devbox tmux"]):
            rc = _cleanup(dry_run=False, settings_path=wt)
        assert rc == 0
        settings = json.loads(wt.read_text(encoding="utf-8"))
        names = [p["name"] for p in settings["profiles"]["list"]]
        assert "devbox tmux" not in names

    def test_tui_empty_selection_prints_nothing_removed(self, tmp_path, capsys):
        wt = _write_wt_settings(tmp_path, [{"name": "devbox tmux"}])
        with patch("wt_tmux_picker.cli.pick_profiles", return_value=[]):
            rc = _cleanup(dry_run=False, settings_path=wt)
        assert rc == 0
        assert "Nothing removed" in capsys.readouterr().out

    def test_hosts_not_found_prints_nothing_to_clean_up(self, tmp_path, capsys):
        wt = _write_wt_settings(tmp_path, [{"name": "other tmux"}])
        rc = _cleanup(dry_run=False, hosts=["devbox"], settings_path=wt)
        assert rc == 0
        assert "Nothing to clean up" in capsys.readouterr().out


class TestPlainSsh:
    def test_calls_ssh_with_host(self):
        with patch("wt_tmux_picker.cli.subprocess.run") as mock_run:
            _plain_ssh("devbox", None)
        assert mock_run.call_args[0][0] == ["ssh", "devbox"]

    def test_calls_ssh_with_user_at_host(self):
        with patch("wt_tmux_picker.cli.subprocess.run") as mock_run:
            _plain_ssh("devbox", "alice")
        assert mock_run.call_args[0][0] == ["ssh", "alice@devbox"]


class TestAttachFunction:
    def _mock_mgr(self, sessions):
        mgr = MagicMock()
        mgr.list_sessions.return_value = sessions
        return mgr

    def test_no_sessions_runs_plain_ssh(self):
        mgr = self._mock_mgr([])
        with (
            patch("wt_tmux_picker.cli.TmuxManager", return_value=mgr),
            patch("wt_tmux_picker.cli._plain_ssh") as mock_plain,
        ):
            rc = _attach("devbox", None)
        assert rc == 0
        mock_plain.assert_called_once_with("devbox", None)

    def test_session_selected_attaches(self):
        mgr = self._mock_mgr(["main"])
        with (
            patch("wt_tmux_picker.cli.TmuxManager", return_value=mgr),
            patch("wt_tmux_picker.cli.pick_session", return_value="main"),
            patch("wt_tmux_picker.cli._plain_ssh") as mock_plain,
        ):
            rc = _attach("devbox", None)
        assert rc == 0
        mgr.attach_session.assert_called_once_with("main")
        mock_plain.assert_not_called()

    def test_session_cancelled_runs_plain_ssh(self):
        mgr = self._mock_mgr(["main"])
        with (
            patch("wt_tmux_picker.cli.TmuxManager", return_value=mgr),
            patch("wt_tmux_picker.cli.pick_session", return_value=None),
            patch("wt_tmux_picker.cli._plain_ssh") as mock_plain,
        ):
            rc = _attach("devbox", None)
        assert rc == 0
        mock_plain.assert_called_once()
        mgr.attach_session.assert_not_called()

    def test_with_user(self):
        mgr = self._mock_mgr([])
        with (
            patch("wt_tmux_picker.cli.TmuxManager", return_value=mgr) as mock_cls,
            patch("wt_tmux_picker.cli._plain_ssh"),
        ):
            _attach("devbox", "alice")
        mock_cls.assert_called_once_with("devbox", "alice")


class TestMainEntrypoint:
    def test_setup_via_main(self, tmp_path):
        cfg = _write_ssh_config(tmp_path, ["host1"])
        wt = _write_wt_settings(tmp_path)

        with (
            patch("wt_tmux_picker.cli.pick_hosts", return_value=["host1"]),
            patch("wt_tmux_picker.cli.has_tmux", return_value=True),
            patch("wt_tmux_picker.cli.has_fzf", return_value=True),
        ):
            rc = main(["setup", "--ssh-config", str(cfg), "--dry-run"])
        assert rc == 0

    def test_cleanup_via_main(self, tmp_path):
        wt = _write_wt_settings(tmp_path)
        with patch("wt_tmux_picker.windows_terminal._default_settings_path", return_value=wt):
            rc = main(["cleanup"])
        assert rc == 0

    def test_attach_via_main(self):
        mgr = MagicMock()
        mgr.list_sessions.return_value = []
        with (
            patch("wt_tmux_picker.cli.TmuxManager", return_value=mgr),
            patch("wt_tmux_picker.cli._plain_ssh"),
        ):
            rc = main(["attach", "devbox"])
        assert rc == 0
