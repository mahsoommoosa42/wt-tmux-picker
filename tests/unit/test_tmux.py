"""Unit tests for tmux.py (delegates to TmuxManager)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from wt_tmux_picker.tmux import capture_pane, has_fzf, has_tmux, list_sessions, session_info


def _manager(*, available=True, sessions=None):
    mgr = MagicMock()
    mgr.is_available.return_value = available
    mgr.command_available.return_value = available
    mgr.list_sessions.return_value = sessions or []
    return mgr


class TestHasTmux:
    def test_found(self):
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=_manager(available=True)):
            assert has_tmux("myhost") is True

    def test_not_found(self):
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=_manager(available=False)):
            assert has_tmux("myhost") is False

    def test_dry_run_skips_manager_and_returns_true(self):
        with patch("wt_tmux_picker.tmux.TmuxManager") as mock_cls:
            result = has_tmux("myhost", dry_run=True)
        mock_cls.assert_not_called()
        assert result is True

    def test_passes_host_and_user(self):
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=_manager()) as mock_cls:
            has_tmux("devbox", "alice")
        mock_cls.assert_called_once_with("devbox", "alice")


class TestHasFzf:
    def test_found(self):
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=_manager(available=True)):
            assert has_fzf("myhost") is True

    def test_not_found(self):
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=_manager(available=False)):
            assert has_fzf("myhost") is False

    def test_dry_run_returns_true(self):
        with patch("wt_tmux_picker.tmux.TmuxManager") as mock_cls:
            result = has_fzf("myhost", dry_run=True)
        mock_cls.assert_not_called()
        assert result is True

    def test_passes_host_and_user(self):
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=_manager()) as mock_cls:
            has_fzf("devbox", "bob")
        mock_cls.assert_called_once_with("devbox", "bob")


class TestListSessions:
    def test_returns_sessions(self):
        mgr = _manager(sessions=["main", "work"])
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=mgr):
            assert list_sessions("myhost") == ["main", "work"]

    def test_returns_empty_when_none(self):
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=_manager(sessions=[])):
            assert list_sessions("myhost") == []

    def test_passes_host_and_user(self):
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=_manager()) as mock_cls:
            list_sessions("devbox", "alice")
        mock_cls.assert_called_once_with("devbox", "alice")


class TestSessionInfo:
    def test_returns_info(self):
        info = {"name": "main", "windows": 2, "created": "now", "attached": False}
        mgr = MagicMock()
        mgr.session_info.return_value = info
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=mgr):
            result = session_info("devbox", name="main")
        assert result == info
        mgr.session_info.assert_called_once_with("main")

    def test_passes_host_and_user(self):
        mgr = MagicMock()
        mgr.session_info.return_value = None
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=mgr) as mock_cls:
            session_info("devbox", "alice", name="work")
        mock_cls.assert_called_once_with("devbox", "alice")


class TestCapturePane:
    def test_returns_content(self):
        mgr = MagicMock()
        mgr.capture_pane.return_value = "$ ls"
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=mgr):
            result = capture_pane("devbox", name="main")
        assert result == "$ ls"
        mgr.capture_pane.assert_called_once_with("main", 50)

    def test_passes_lines(self):
        mgr = MagicMock()
        mgr.capture_pane.return_value = ""
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=mgr):
            capture_pane("devbox", name="main", lines=10)
        mgr.capture_pane.assert_called_once_with("main", 10)

    def test_passes_host_and_user(self):
        mgr = MagicMock()
        mgr.capture_pane.return_value = ""
        with patch("wt_tmux_picker.tmux.TmuxManager", return_value=mgr) as mock_cls:
            capture_pane("devbox", "alice", name="main")
        mock_cls.assert_called_once_with("devbox", "alice")
