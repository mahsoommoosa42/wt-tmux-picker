"""Unit tests for tmux.py (delegates to TmuxManager)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from wt_tmux_picker.tmux import has_fzf, has_tmux, list_sessions


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
