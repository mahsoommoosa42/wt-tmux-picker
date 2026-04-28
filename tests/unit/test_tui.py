"""Unit tests for tui.py."""

from unittest.mock import MagicMock, patch

from wt_tmux_picker.tui import pick_profiles, pick_session


class TestPickSession:
    def test_returns_selected_session(self):
        mock_dialog = MagicMock()
        mock_dialog.run.return_value = "main"
        with patch("wt_tmux_picker.tui.radiolist_dialog", return_value=mock_dialog):
            result = pick_session(["main", "work"], "devbox")
        assert result == "main"

    def test_returns_none_when_user_cancels(self):
        mock_dialog = MagicMock()
        mock_dialog.run.return_value = None
        with patch("wt_tmux_picker.tui.radiolist_dialog", return_value=mock_dialog):
            result = pick_session(["main"], "devbox")
        assert result is None

    def test_passes_host_in_title(self):
        mock_dialog = MagicMock()
        mock_dialog.run.return_value = None
        with patch("wt_tmux_picker.tui.radiolist_dialog", return_value=mock_dialog) as mock_rd:
            pick_session(["main"], "myhost")
        call_kwargs = mock_rd.call_args.kwargs
        assert "myhost" in call_kwargs["title"]

    def test_passes_sessions_as_values(self):
        mock_dialog = MagicMock()
        mock_dialog.run.return_value = None
        with patch("wt_tmux_picker.tui.radiolist_dialog", return_value=mock_dialog) as mock_rd:
            pick_session(["main", "work"], "devbox")
        call_kwargs = mock_rd.call_args.kwargs
        assert ("main", "main") in call_kwargs["values"]
        assert ("work", "work") in call_kwargs["values"]


class TestPickProfiles:
    def test_returns_selected_profiles(self):
        mock_dialog = MagicMock()
        mock_dialog.run.return_value = ["devbox tmux", "prod tmux"]
        with patch("wt_tmux_picker.tui.checkboxlist_dialog", return_value=mock_dialog):
            result = pick_profiles(["devbox tmux", "prod tmux", "staging tmux"])
        assert result == ["devbox tmux", "prod tmux"]

    def test_returns_empty_list_when_user_cancels(self):
        mock_dialog = MagicMock()
        mock_dialog.run.return_value = None
        with patch("wt_tmux_picker.tui.checkboxlist_dialog", return_value=mock_dialog):
            result = pick_profiles(["devbox tmux"])
        assert result == []

    def test_returns_empty_list_when_nothing_selected(self):
        mock_dialog = MagicMock()
        mock_dialog.run.return_value = []
        with patch("wt_tmux_picker.tui.checkboxlist_dialog", return_value=mock_dialog):
            result = pick_profiles(["devbox tmux"])
        assert result == []

    def test_passes_profiles_as_values(self):
        mock_dialog = MagicMock()
        mock_dialog.run.return_value = []
        with patch(
            "wt_tmux_picker.tui.checkboxlist_dialog", return_value=mock_dialog
        ) as mock_cd:
            pick_profiles(["devbox tmux", "prod tmux"])
        call_kwargs = mock_cd.call_args.kwargs
        assert ("devbox tmux", "devbox tmux") in call_kwargs["values"]
        assert ("prod tmux", "prod tmux") in call_kwargs["values"]
