"""Unit tests for tmux.py."""

import socket
from unittest.mock import MagicMock, patch

import paramiko

from wt_tmux_picker.tmux import _ssh_exec, has_fzf, has_tmux, list_sessions


def _mock_exec(exit_status: int, stdout: str = "") -> tuple[int, str]:
    return exit_status, stdout


class TestSshExec:
    def _make_client(self, exit_status: int = 0, output: bytes = b"") -> MagicMock:
        mock_channel = MagicMock()
        mock_channel.recv_exit_status.return_value = exit_status
        mock_stdout = MagicMock()
        mock_stdout.channel = mock_channel
        mock_stdout.read.return_value = output
        mock_client = MagicMock()
        mock_client.exec_command.return_value = (None, mock_stdout, None)
        return mock_client

    def test_returns_exit_status_and_output(self):
        client = self._make_client(0, b"result\n")
        with patch("wt_tmux_picker.tmux.paramiko.SSHClient", return_value=client):
            status, output = _ssh_exec("host", None, "cmd")
        assert status == 0
        assert output == "result\n"

    def test_ssh_exception_returns_minus_one(self):
        client = MagicMock()
        client.connect.side_effect = paramiko.SSHException("err")
        with patch("wt_tmux_picker.tmux.paramiko.SSHClient", return_value=client):
            status, output = _ssh_exec("host", None, "cmd")
        assert status == -1
        assert output == ""

    def test_socket_timeout_returns_minus_one(self):
        client = MagicMock()
        client.connect.side_effect = socket.timeout()
        with patch("wt_tmux_picker.tmux.paramiko.SSHClient", return_value=client):
            status, output = _ssh_exec("host", None, "cmd")
        assert status == -1
        assert output == ""

    def test_oserror_returns_minus_one(self):
        client = MagicMock()
        client.connect.side_effect = OSError("unreachable")
        with patch("wt_tmux_picker.tmux.paramiko.SSHClient", return_value=client):
            status, output = _ssh_exec("host", None, "cmd")
        assert status == -1
        assert output == ""

    def test_client_always_closed(self):
        client = self._make_client()
        with patch("wt_tmux_picker.tmux.paramiko.SSHClient", return_value=client):
            _ssh_exec("host", None, "cmd")
        client.close.assert_called_once()

    def test_client_closed_on_exception(self):
        client = MagicMock()
        client.connect.side_effect = OSError()
        with patch("wt_tmux_picker.tmux.paramiko.SSHClient", return_value=client):
            _ssh_exec("host", None, "cmd")
        client.close.assert_called_once()

    def test_passes_user_to_connect(self):
        client = self._make_client()
        with patch("wt_tmux_picker.tmux.paramiko.SSHClient", return_value=client):
            _ssh_exec("myhost", "alice", "cmd")
        call_kwargs = client.connect.call_args.kwargs
        assert call_kwargs["username"] == "alice"
        assert call_kwargs["hostname"] == "myhost"


class TestHasTmux:
    def test_tmux_found(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(0, "")):
            assert has_tmux("myhost") is True

    def test_tmux_not_found(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(1, "")):
            assert has_tmux("myhost") is False

    def test_connection_failure_returns_false(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(-1, "")):
            assert has_tmux("myhost") is False

    def test_with_user(self):
        captured = {}

        def capture(host, user, command):
            captured["host"] = host
            captured["user"] = user
            return 0, ""

        with patch("wt_tmux_picker.tmux._ssh_exec", side_effect=capture):
            has_tmux("myhost", user="admin")

        assert captured["user"] == "admin"
        assert captured["host"] == "myhost"

    def test_without_user(self):
        captured = {}

        def capture(host, user, command):
            captured["user"] = user
            return 0, ""

        with patch("wt_tmux_picker.tmux._ssh_exec", side_effect=capture):
            has_tmux("myhost")

        assert captured["user"] is None

    def test_dry_run_skips_ssh_and_returns_true(self):
        with patch("wt_tmux_picker.tmux._ssh_exec") as mock_exec:
            result = has_tmux("myhost", dry_run=True)
        mock_exec.assert_not_called()
        assert result is True

    def test_checks_tmux_command(self):
        captured = {}

        def capture(host, user, command):
            captured["command"] = command
            return 0, ""

        with patch("wt_tmux_picker.tmux._ssh_exec", side_effect=capture):
            has_tmux("myhost")

        assert "tmux" in captured["command"]


class TestHasFzf:
    def test_fzf_found(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(0, "")):
            assert has_fzf("myhost") is True

    def test_fzf_not_found(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(1, "")):
            assert has_fzf("myhost") is False

    def test_dry_run_returns_true(self):
        with patch("wt_tmux_picker.tmux._ssh_exec") as mock_exec:
            result = has_fzf("myhost", dry_run=True)
        mock_exec.assert_not_called()
        assert result is True

    def test_connection_failure_returns_false(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(-1, "")):
            assert has_fzf("myhost") is False

    def test_with_user(self):
        captured = {}

        def capture(host, user, command):
            captured["user"] = user
            return 0, ""

        with patch("wt_tmux_picker.tmux._ssh_exec", side_effect=capture):
            has_fzf("myhost", user="bob")

        assert captured["user"] == "bob"

    def test_checks_fzf_command(self):
        captured = {}

        def capture(host, user, command):
            captured["command"] = command
            return 0, ""

        with patch("wt_tmux_picker.tmux._ssh_exec", side_effect=capture):
            has_fzf("myhost")

        assert "fzf" in captured["command"]


class TestListSessions:
    def test_returns_session_names(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(0, "main\nwork\nlogs\n")):
            assert list_sessions("myhost") == ["main", "work", "logs"]

    def test_empty_output_returns_empty_list(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(0, "")):
            assert list_sessions("myhost") == []

    def test_nonzero_exit_returns_empty_list(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(1, "")):
            assert list_sessions("myhost") == []

    def test_connection_failure_returns_empty_list(self):
        with patch("wt_tmux_picker.tmux._ssh_exec", return_value=(-1, "")):
            assert list_sessions("myhost") == []

    def test_with_user(self):
        captured = {}

        def capture(host, user, command):
            captured["user"] = user
            return 0, "main\n"

        with patch("wt_tmux_picker.tmux._ssh_exec", side_effect=capture):
            list_sessions("myhost", user="alice")

        assert captured["user"] == "alice"
