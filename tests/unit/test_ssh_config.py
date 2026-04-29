"""Unit tests for ssh_config.py."""

import pytest
from pathlib import Path
from unittest.mock import patch

from wt_tmux_picker.ssh_config import parse_ssh_hosts


def _write_config(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config"
    p.write_text(content, encoding="utf-8")
    return p


class TestParseSSHHosts:
    def test_single_host(self, tmp_path):
        cfg = _write_config(tmp_path, "Host myserver\n    User foo\n")
        assert parse_ssh_hosts(cfg) == ["myserver"]

    def test_multiple_hosts(self, tmp_path):
        cfg = _write_config(
            tmp_path,
            "Host alpha\n    User a\nHost beta\n    User b\n",
        )
        assert parse_ssh_hosts(cfg) == ["alpha", "beta"]

    def test_wildcard_star_skipped(self, tmp_path):
        cfg = _write_config(tmp_path, "Host *\n    ServerAliveInterval 60\n")
        assert parse_ssh_hosts(cfg) == []

    def test_wildcard_question_mark_skipped(self, tmp_path):
        cfg = _write_config(tmp_path, "Host host?\n    User foo\n")
        assert parse_ssh_hosts(cfg) == []

    def test_mixed_wildcards_and_real_hosts(self, tmp_path):
        cfg = _write_config(
            tmp_path,
            "Host *\n    ServerAliveInterval 60\nHost real-host\n    User bar\n",
        )
        assert parse_ssh_hosts(cfg) == ["real-host"]

    def test_empty_config(self, tmp_path):
        cfg = _write_config(tmp_path, "")
        assert parse_ssh_hosts(cfg) == []

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_ssh_hosts(tmp_path / "nonexistent")

    def test_default_path_used(self, tmp_path):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "config").write_text("Host dev\n", encoding="utf-8")
        with patch("wt_tmux_picker.ssh_config.Path.home", return_value=tmp_path):
            result = parse_ssh_hosts()
        assert result == ["dev"]

    def test_case_insensitive_host_keyword(self, tmp_path):
        cfg = _write_config(tmp_path, "HOST caseserver\n    User x\n")
        assert parse_ssh_hosts(cfg) == ["caseserver"]

    def test_multiple_tokens_on_host_line(self, tmp_path):
        cfg = _write_config(tmp_path, "Host alpha beta gamma\n    User x\n")
        assert parse_ssh_hosts(cfg) == ["alpha", "beta", "gamma"]

    def test_multiple_tokens_with_wildcard_excluded(self, tmp_path):
        cfg = _write_config(tmp_path, "Host alpha * gamma\n    User x\n")
        assert parse_ssh_hosts(cfg) == ["alpha", "gamma"]

    def test_include_directive(self, tmp_path):
        included = tmp_path / "extra.conf"
        included.write_text("Host included-host\n    User x\n", encoding="utf-8")
        cfg = _write_config(
            tmp_path,
            f"Include {included}\nHost main-host\n    User y\n",
        )
        result = parse_ssh_hosts(cfg)
        assert "included-host" in result
        assert "main-host" in result

    def test_include_glob_pattern(self, tmp_path):
        conf_dir = tmp_path / "conf.d"
        conf_dir.mkdir()
        (conf_dir / "a.conf").write_text("Host host-a\n", encoding="utf-8")
        (conf_dir / "b.conf").write_text("Host host-b\n", encoding="utf-8")
        cfg = _write_config(
            tmp_path,
            f"Include {conf_dir}/*.conf\n",
        )
        result = parse_ssh_hosts(cfg)
        assert "host-a" in result
        assert "host-b" in result

    def test_include_tilde_expansion(self, tmp_path):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        conf_d = ssh_dir / "conf.d"
        conf_d.mkdir()
        (conf_d / "extra.conf").write_text("Host tilde-host\n", encoding="utf-8")
        cfg = ssh_dir / "config"
        cfg.write_text("Include ~/.ssh/conf.d/*.conf\n", encoding="utf-8")
        with patch("wt_tmux_picker.ssh_config.Path.home", return_value=tmp_path):
            result = parse_ssh_hosts(cfg)
        assert "tilde-host" in result

    def test_include_relative_path(self, tmp_path):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "extra.conf").write_text("Host rel-host\n", encoding="utf-8")
        cfg = ssh_dir / "config"
        cfg.write_text("Include extra.conf\n", encoding="utf-8")
        with patch("wt_tmux_picker.ssh_config.Path.home", return_value=tmp_path):
            result = parse_ssh_hosts(cfg)
        assert "rel-host" in result

    def test_include_nonexistent_ignored(self, tmp_path):
        cfg = _write_config(
            tmp_path,
            f"Include {tmp_path}/nonexistent/*.conf\nHost real\n",
        )
        assert parse_ssh_hosts(cfg) == ["real"]

    def test_include_circular_safe(self, tmp_path):
        cfg = _write_config(
            tmp_path,
            f"Include {tmp_path / 'config'}\nHost safe\n",
        )
        assert parse_ssh_hosts(cfg) == ["safe"]

    def test_include_case_insensitive(self, tmp_path):
        included = tmp_path / "extra.conf"
        included.write_text("Host ci-host\n", encoding="utf-8")
        cfg = _write_config(tmp_path, f"INCLUDE {included}\n")
        assert parse_ssh_hosts(cfg) == ["ci-host"]

    def test_include_skips_directories(self, tmp_path):
        sub = tmp_path / "subdir.conf"
        sub.mkdir()
        cfg = _write_config(
            tmp_path,
            f"Include {tmp_path}/*.conf\nHost real\n",
        )
        assert parse_ssh_hosts(cfg) == ["real"]
