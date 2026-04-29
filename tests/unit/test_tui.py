"""Unit tests for tui.py."""

from unittest.mock import MagicMock, patch

from wt_tmux_picker.tui import (
    ProfilePicker,
    SessionPicker,
    pick_profiles,
    pick_session,
)


class TestSessionPicker:
    def test_stores_sessions_and_host(self):
        app = SessionPicker(["a", "b"], "myhost")
        assert app.sessions == ["a", "b"]
        assert app.host == "myhost"

    def test_compose_yields_four_widgets(self):
        app = SessionPicker(["a", "b"], "host")
        widgets = list(app.compose())
        assert len(widgets) == 4

    def test_option_selected_exits_with_id(self):
        app = SessionPicker(["main"], "host")
        app.exit = MagicMock()
        event = MagicMock()
        event.option.id = "main"
        app.on_option_list_option_selected(event)
        app.exit.assert_called_once_with("main")

    def test_cancel_exits_none(self):
        app = SessionPicker(["main"], "host")
        app.exit = MagicMock()
        app.action_cancel()
        app.exit.assert_called_once_with(None)


class TestProfilePicker:
    def test_stores_profiles(self):
        app = ProfilePicker(["a tmux"])
        assert app.profiles == ["a tmux"]

    def test_compose_yields_five_widgets(self):
        app = ProfilePicker(["a tmux"])
        widgets = list(app.compose())
        assert len(widgets) == 5

    def test_button_pressed_exits_with_selected(self):
        app = ProfilePicker(["a tmux", "b tmux"])
        mock_sel = MagicMock()
        mock_sel.selected = ["a tmux"]
        app.query_one = MagicMock(return_value=mock_sel)
        app.exit = MagicMock()
        app.on_button_pressed(MagicMock())
        app.exit.assert_called_once_with(["a tmux"])

    def test_cancel_exits_empty_list(self):
        app = ProfilePicker(["a tmux"])
        app.exit = MagicMock()
        app.action_cancel()
        app.exit.assert_called_once_with([])


class TestPickSession:
    def test_returns_selected_session(self):
        with patch("wt_tmux_picker.tui.SessionPicker") as MockApp:
            MockApp.return_value.run.return_value = "main"
            result = pick_session(["main", "work"], "devbox")
        assert result == "main"
        MockApp.assert_called_once_with(["main", "work"], "devbox")

    def test_returns_none_when_cancelled(self):
        with patch("wt_tmux_picker.tui.SessionPicker") as MockApp:
            MockApp.return_value.run.return_value = None
            result = pick_session(["main"], "devbox")
        assert result is None


class TestPickProfiles:
    def test_returns_selected_profiles(self):
        with patch("wt_tmux_picker.tui.ProfilePicker") as MockApp:
            MockApp.return_value.run.return_value = ["devbox tmux", "prod tmux"]
            result = pick_profiles(["devbox tmux", "prod tmux", "staging tmux"])
        assert result == ["devbox tmux", "prod tmux"]
        MockApp.assert_called_once_with(
            ["devbox tmux", "prod tmux", "staging tmux"]
        )

    def test_returns_empty_when_cancelled(self):
        with patch("wt_tmux_picker.tui.ProfilePicker") as MockApp:
            MockApp.return_value.run.return_value = None
            result = pick_profiles(["devbox tmux"])
        assert result == []

    def test_returns_empty_when_none_selected(self):
        with patch("wt_tmux_picker.tui.ProfilePicker") as MockApp:
            MockApp.return_value.run.return_value = []
            result = pick_profiles(["devbox tmux"])
        assert result == []
