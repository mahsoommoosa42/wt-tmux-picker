"""Unit tests for host_info.py."""

from unittest.mock import MagicMock, patch

from wt_tmux_picker.host_info import (
    HostInfo,
    _map_platform,
    _parse_probe,
    _probe_ssh,
    _resolve_hostname,
    _resolve_ip,
    _ssh_target,
    probe_host,
)


class TestHostInfo:
    def test_eligible_when_key_auth_and_both_present(self):
        info = HostInfo(name="h", auth="key", has_tmux=True, has_fzf=True)
        assert info.eligible is True

    def test_not_eligible_without_key_auth(self):
        info = HostInfo(name="h", auth="unknown", has_tmux=True, has_fzf=True)
        assert info.eligible is False

    def test_not_eligible_windows_even_with_tools(self):
        info = HostInfo(name="h", platform="Windows", auth="key",
                        has_tmux=True, has_fzf=True)
        assert info.eligible is False

    def test_not_eligible_without_tmux(self):
        info = HostInfo(name="h", has_tmux=False, has_fzf=True)
        assert info.eligible is False

    def test_not_eligible_without_fzf(self):
        info = HostInfo(name="h", has_tmux=True, has_fzf=False)
        assert info.eligible is False

    def test_missing_tools_both(self):
        info = HostInfo(name="h")
        assert info.missing_tools == ["tmux", "fzf"]

    def test_missing_tools_tmux_only(self):
        info = HostInfo(name="h", has_tmux=False, has_fzf=True)
        assert info.missing_tools == ["tmux"]

    def test_missing_tools_fzf_only(self):
        info = HostInfo(name="h", has_tmux=True, has_fzf=False)
        assert info.missing_tools == ["fzf"]

    def test_missing_tools_none(self):
        info = HostInfo(name="h", has_tmux=True, has_fzf=True)
        assert info.missing_tools == []

    def test_label_view_0(self):
        info = HostInfo(name="host1", platform="Linux")
        assert info.label(0) == "host1  [Linux]"

    def test_label_view_1(self):
        info = HostInfo(name="host1", platform="Linux", ip="1.2.3.4")
        assert info.label(1) == "host1  [Linux]  (1.2.3.4)"

    def test_label_view_2(self):
        info = HostInfo(name="host1", platform="Linux", ip="1.2.3.4", auth="key")
        assert info.label(2) == "host1  [Linux]  (1.2.3.4)  auth: key"

    def test_rejection_reason_no_key_auth(self):
        info = HostInfo(name="h", platform="Linux", auth="unknown")
        assert info.rejection_reason == "key auth failed"

    def test_rejection_reason_windows(self):
        info = HostInfo(name="h", platform="Windows", auth="key")
        assert info.rejection_reason == "Windows \u2014 tmux not supported"

    def test_rejection_reason_missing_tools(self):
        info = HostInfo(name="h", platform="Linux", auth="key",
                        has_tmux=False, has_fzf=False)
        assert info.rejection_reason == "tmux, fzf not found"

    def test_rejection_reason_eligible(self):
        info = HostInfo(name="h", platform="Linux", auth="key",
                        has_tmux=True, has_fzf=True)
        assert info.rejection_reason == ""

    def test_unavailable_label_linux(self):
        info = HostInfo(name="host1", platform="Linux", auth="key",
                        has_tmux=False, has_fzf=False)
        result = info.unavailable_label(0)
        assert "tmux, fzf not found" in result
        assert "host1" in result

    def test_unavailable_label_windows(self):
        info = HostInfo(name="winbox", platform="Windows", auth="key")
        result = info.unavailable_label(0)
        assert "Windows \u2014 tmux not supported" in result
        assert "winbox" in result

    def test_unavailable_label_auth_failed(self):
        info = HostInfo(name="nokey", platform="Unknown")
        result = info.unavailable_label(0)
        assert "key auth failed" in result
        assert "nokey" in result


class TestSshTarget:
    def test_with_user(self):
        assert _ssh_target("h", "alice") == "alice@h"

    def test_without_user(self):
        assert _ssh_target("h", None) == "h"


class TestResolveHostname:
    def test_parses_ssh_g_output(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hostname 10.0.0.1\nuser alice\n"
        with patch("wt_tmux_picker.host_info.subprocess.run", return_value=mock_result):
            assert _resolve_hostname("alias") == "10.0.0.1"

    def test_no_hostname_line_falls_back(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "user alice\nport 22\n"
        with patch("wt_tmux_picker.host_info.subprocess.run", return_value=mock_result):
            assert _resolve_hostname("alias") == "alias"

    def test_fallback_on_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("wt_tmux_picker.host_info.subprocess.run", return_value=mock_result):
            assert _resolve_hostname("alias") == "alias"

    def test_fallback_on_os_error(self):
        with patch("wt_tmux_picker.host_info.subprocess.run", side_effect=OSError):
            assert _resolve_hostname("alias") == "alias"

    def test_fallback_on_timeout(self):
        import subprocess
        with patch(
            "wt_tmux_picker.host_info.subprocess.run",
            side_effect=subprocess.TimeoutExpired("ssh", 5),
        ):
            assert _resolve_hostname("alias") == "alias"


class TestResolveIp:
    def test_resolves_ip(self):
        with patch(
            "wt_tmux_picker.host_info.socket.getaddrinfo",
            return_value=[(None, None, None, None, ("1.2.3.4", 0))],
        ):
            assert _resolve_ip("host") == "1.2.3.4"

    def test_empty_results_returns_na(self):
        with patch(
            "wt_tmux_picker.host_info.socket.getaddrinfo",
            return_value=[],
        ):
            assert _resolve_ip("host") == "N/A"

    def test_fallback_on_gaierror(self):
        import socket
        with patch(
            "wt_tmux_picker.host_info.socket.getaddrinfo",
            side_effect=socket.gaierror,
        ):
            assert _resolve_ip("host") == "N/A"

    def test_fallback_on_os_error(self):
        with patch(
            "wt_tmux_picker.host_info.socket.getaddrinfo",
            side_effect=OSError,
        ):
            assert _resolve_ip("host") == "N/A"


class TestMapPlatform:
    def test_linux(self):
        assert _map_platform("Linux") == "Linux"

    def test_darwin(self):
        assert _map_platform("Darwin") == "macOS"

    def test_mingw(self):
        assert _map_platform("MINGW64_NT") == "Windows"

    def test_msys(self):
        assert _map_platform("MSYS_NT") == "Windows"

    def test_cygwin(self):
        assert _map_platform("CYGWIN_NT") == "Windows"

    def test_windows(self):
        assert _map_platform("Windows_NT") == "Windows"

    def test_unknown_returns_raw(self):
        assert _map_platform("FreeBSD") == "FreeBSD"

    def test_empty_returns_unknown(self):
        assert _map_platform("") == "Unknown"

    def test_whitespace_returns_unknown(self):
        assert _map_platform("   ") == "Unknown"


class TestProbeSsh:
    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Linux\nyes\nyes\n"
        with patch("wt_tmux_picker.host_info.subprocess.run", return_value=mock_result) as m:
            code, out = _probe_ssh("h", "alice")
        assert code == 0
        assert "Linux" in out
        args = m.call_args[0][0]
        assert "BatchMode=yes" not in " ".join(args)

    def test_batch_mode(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Linux\nyes\nyes\n"
        with patch("wt_tmux_picker.host_info.subprocess.run", return_value=mock_result) as m:
            _probe_ssh("h", None, batch_mode=True)
        args = m.call_args[0][0]
        assert "-o" in args
        idx = args.index("BatchMode=yes")
        assert idx > 0

    def test_identity_file(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Linux\nyes\nyes\n"
        with patch("wt_tmux_picker.host_info.subprocess.run", return_value=mock_result) as m:
            _probe_ssh("h", None, identity_file="/tmp/key")
        args = m.call_args[0][0]
        assert "-i" in args
        assert "/tmp/key" in args

    def test_os_error(self):
        with patch("wt_tmux_picker.host_info.subprocess.run", side_effect=OSError):
            code, out = _probe_ssh("h", None)
        assert code == -1
        assert out == ""

    def test_timeout(self):
        import subprocess
        with patch(
            "wt_tmux_picker.host_info.subprocess.run",
            side_effect=subprocess.TimeoutExpired("ssh", 15),
        ):
            code, out = _probe_ssh("h", None)
        assert code == -1
        assert out == ""


class TestParseProbe:
    def test_full_output(self):
        platform, tmux, fzf = _parse_probe("Linux\nyes\nno\n")
        assert platform == "Linux"
        assert tmux is True
        assert fzf is False

    def test_empty_output(self):
        platform, tmux, fzf = _parse_probe("")
        assert platform == "Unknown"
        assert tmux is False
        assert fzf is False

    def test_partial_output_one_line(self):
        platform, tmux, fzf = _parse_probe("Darwin\n")
        assert platform == "macOS"
        assert tmux is False
        assert fzf is False

    def test_partial_output_two_lines(self):
        platform, tmux, fzf = _parse_probe("Linux\nyes\n")
        assert platform == "Linux"
        assert tmux is True
        assert fzf is False


class TestProbeHost:
    def test_dry_run_returns_defaults(self):
        info = probe_host("h", "alice", dry_run=True)
        assert info.name == "h"
        assert info.user == "alice"
        assert info.auth == "key"
        assert info.has_tmux is True
        assert info.has_fzf is True

    def test_key_auth_success(self):
        with (
            patch(
                "wt_tmux_picker.host_info._resolve_hostname",
                return_value="real.host",
            ),
            patch("wt_tmux_picker.host_info._resolve_ip", return_value="1.2.3.4"),
            patch(
                "wt_tmux_picker.host_info._probe_ssh",
                return_value=(0, "Linux\nyes\nyes\n"),
            ),
        ):
            info = probe_host("alias", "alice")

        assert info.name == "alias"
        assert info.platform == "Linux"
        assert info.ip == "1.2.3.4"
        assert info.auth == "key"
        assert info.has_tmux is True
        assert info.has_fzf is True

    def test_key_auth_failure_marks_unreachable(self):
        with (
            patch("wt_tmux_picker.host_info._resolve_hostname", return_value="h"),
            patch("wt_tmux_picker.host_info._resolve_ip", return_value="N/A"),
            patch(
                "wt_tmux_picker.host_info._probe_ssh",
                return_value=(255, ""),
            ),
        ):
            info = probe_host("h")

        assert info.auth == "unknown"
        assert info.has_tmux is False
        assert info.has_fzf is False
        assert info.eligible is False
        assert info.rejection_reason == "key auth failed"

    def test_unreachable_host(self):
        with (
            patch("wt_tmux_picker.host_info._resolve_hostname", return_value="h"),
            patch("wt_tmux_picker.host_info._resolve_ip", return_value="1.1.1.1"),
            patch("wt_tmux_picker.host_info._probe_ssh", return_value=(-1, "")),
        ):
            info = probe_host("h")

        assert info.auth == "unknown"
        assert info.has_tmux is False
        assert info.has_fzf is False
        assert info.ip == "1.1.1.1"
