"""Unit tests for tui.py."""

from unittest.mock import MagicMock, patch

from wt_tmux_picker.tui import (
    HostPicker,
    ProfilePicker,
    SessionPicker,
    pick_hosts,
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


class TestHostPicker:
    def test_stores_eligible_and_unavailable(self):
        app = HostPicker(["alpha"], [("beta", "tmux not found")])
        assert app.eligible == ["alpha"]
        assert app.unavailable == [("beta", "tmux not found")]

    def test_unavailable_defaults_to_empty(self):
        app = HostPicker(["alpha"])
        assert app.unavailable == []

    def test_compose_eligible_only(self):
        app = HostPicker(["alpha"])
        widgets = list(app.compose())
        # Header, info, SelectionList, Confirm, Footer
        assert len(widgets) == 5

    def test_compose_with_unavailable(self):
        app = HostPicker(["alpha"], [("beta", "tmux not found")])
        widgets = list(app.compose())
        # Header, info, SelectionList, unavailable Static, Confirm, Footer
        assert len(widgets) == 6

    def test_compose_no_eligible(self):
        app = HostPicker([], [("beta", "tmux not found")])
        widgets = list(app.compose())
        # Header, info, unavailable Static, Confirm, Footer
        assert len(widgets) == 5

    def test_button_pressed_exits_with_selected(self):
        app = HostPicker(["alpha", "beta"])
        mock_sel = MagicMock()
        mock_sel.selected = ["alpha"]
        mock_nodes = MagicMock()
        mock_nodes.__bool__ = lambda self: True
        mock_nodes.first.return_value = mock_sel
        app.query = MagicMock(return_value=mock_nodes)
        app.exit = MagicMock()
        app.on_button_pressed(MagicMock())
        app.exit.assert_called_once_with(["alpha"])

    def test_button_pressed_no_eligible_exits_empty(self):
        app = HostPicker([], [("beta", "tmux not found")])
        mock_nodes = MagicMock()
        mock_nodes.__bool__ = lambda self: False
        app.query = MagicMock(return_value=mock_nodes)
        app.exit = MagicMock()
        app.on_button_pressed(MagicMock())
        app.exit.assert_called_once_with([])

    def test_cancel_exits_empty_list(self):
        app = HostPicker(["alpha"])
        app.exit = MagicMock()
        app.action_cancel()
        app.exit.assert_called_once_with([])


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


class TestPickHosts:
    def test_returns_selected_hosts(self):
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = ["alpha", "beta"]
            result = pick_hosts(["alpha", "beta", "gamma"])
        assert result == ["alpha", "beta"]
        MockApp.assert_called_once_with(["alpha", "beta", "gamma"], None)

    def test_passes_unavailable(self):
        unavail = [("bad", "tmux not found")]
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = ["alpha"]
            result = pick_hosts(["alpha"], unavail)
        assert result == ["alpha"]
        MockApp.assert_called_once_with(["alpha"], unavail)

    def test_returns_empty_when_cancelled(self):
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = None
            result = pick_hosts(["alpha"])
        assert result == []

    def test_returns_empty_when_none_selected(self):
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = []
            result = pick_hosts(["alpha"])
        assert result == []


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
