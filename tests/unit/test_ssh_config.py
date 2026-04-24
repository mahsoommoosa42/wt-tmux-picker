"""Unit tests for ssh_config.py."""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

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
