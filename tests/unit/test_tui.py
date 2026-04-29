"""Unit tests for tui.py."""

import pytest
from unittest.mock import MagicMock, patch

from textual.widgets import Button, Input, OptionList, SelectionList, Static

from wt_tmux_picker.host_info import HostInfo
from wt_tmux_picker.tui import (
    HostPicker,
    ManualHostScreen,
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
    @staticmethod
    def _eligible(name: str = "alpha") -> HostInfo:
        return HostInfo(name=name, platform="Linux", has_tmux=True, has_fzf=True)

    @staticmethod
    def _unavailable(name: str = "beta", tmux: bool = False) -> HostInfo:
        return HostInfo(name=name, platform="Linux", has_tmux=tmux, has_fzf=False)

    def test_separates_eligible_and_unavailable(self):
        e = self._eligible()
        u = self._unavailable()
        app = HostPicker([e, u])
        assert app._eligible == [e]
        assert app._unavailable == [u]

    def test_eligible_only_no_unavailable(self):
        app = HostPicker([self._eligible()])
        assert len(app._eligible) == 1
        assert len(app._unavailable) == 0

    def test_has_unavailable_section(self):
        app = HostPicker([self._eligible(), self._unavailable()])
        assert len(app._eligible) == 1
        assert len(app._unavailable) == 1

    def test_action_cancel_exits_empty(self):
        app = HostPicker([self._eligible()])
        app.exit = MagicMock()
        app.action_cancel()
        app.exit.assert_called_once_with([])

    def test_action_cycle_view_increments(self):
        app = HostPicker([self._eligible()])
        assert app._view == 0
        # Mock query methods to prevent widget errors
        mock_static = MagicMock()
        mock_sl = MagicMock()
        mock_sl.selected = set()
        mock_sl.option_count = 1

        def fake_query_one(selector, *args):
            if selector == "#view-label":
                return mock_static
            if selector == "#host-list":
                return mock_sl
            return MagicMock()

        app.query_one = fake_query_one
        app.query = MagicMock(return_value=MagicMock(__bool__=lambda s: False))
        app.action_cycle_view()
        assert app._view == 1
        app.action_cycle_view()
        assert app._view == 2
        app.action_cycle_view()
        assert app._view == 0

    def test_on_manual_host_none_ignored(self):
        app = HostPicker([self._eligible()])
        app._on_manual_host(None)
        assert app._manual == []

    def test_on_manual_host_adds_entry(self):
        app = HostPicker([self._eligible()])
        mock_sl = MagicMock()
        mock_sl.selected = set()
        mock_sl.option_count = 1
        app.query_one = MagicMock(return_value=mock_sl)
        app._on_manual_host(("newhost", "alice"))
        assert len(app._manual) == 1
        assert app._manual[0].name == "newhost"
        assert app._manual[0].user == "alice"
        assert app._manual[0].manual is True

    def test_confirm_returns_selected_eligible(self):
        e = self._eligible("alpha")
        app = HostPicker([e])
        app.exit = MagicMock()
        mock_sl = MagicMock()
        mock_sl.selected = {"alpha"}
        app.query_one = MagicMock(return_value=mock_sl)
        app._confirm()
        app.exit.assert_called_once()
        result = app.exit.call_args[0][0]
        assert len(result) == 1
        assert result[0].name == "alpha"

    def test_confirm_empty_selection(self):
        app = HostPicker([self._eligible()])
        app.exit = MagicMock()
        mock_sl = MagicMock()
        mock_sl.selected = set()
        app.query_one = MagicMock(return_value=mock_sl)
        app._confirm()
        app.exit.assert_called_once_with([])

    def test_on_button_pressed_unknown_id_is_noop(self):
        app = HostPicker([self._eligible()])
        app.exit = MagicMock()
        event = MagicMock()
        event.button.id = "unknown"
        app.on_button_pressed(event)
        app.exit.assert_not_called()

    def test_unavailable_text_shows_missing_tools(self):
        u = HostInfo(name="bad", platform="Linux", has_tmux=False, has_fzf=False)
        app = HostPicker([u])
        text = app._unavailable_text()
        assert "bad" in text
        assert "tmux, fzf not found" in text
        assert "Unavailable:" in text


class TestManualHostScreen:
    def test_add_button_with_hostname(self):
        screen = ManualHostScreen()
        mock_hostname = MagicMock()
        mock_hostname.value = "devbox"
        mock_username = MagicMock()
        mock_username.value = "alice"

        def fake_query_one(selector, cls):
            if selector == "#hostname":
                return mock_hostname
            return mock_username

        screen.query_one = fake_query_one
        screen.dismiss = MagicMock()
        event = MagicMock()
        event.button.id = "add"
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(("devbox", "alice"))

    def test_add_button_empty_hostname_ignored(self):
        screen = ManualHostScreen()
        mock_hostname = MagicMock()
        mock_hostname.value = "  "
        screen.query_one = MagicMock(return_value=mock_hostname)
        screen.dismiss = MagicMock()
        event = MagicMock()
        event.button.id = "add"
        screen.on_button_pressed(event)
        screen.dismiss.assert_not_called()

    def test_add_button_no_username(self):
        screen = ManualHostScreen()
        mock_hostname = MagicMock()
        mock_hostname.value = "devbox"
        mock_username = MagicMock()
        mock_username.value = ""

        def fake_query_one(selector, cls):
            if selector == "#hostname":
                return mock_hostname
            return mock_username

        screen.query_one = fake_query_one
        screen.dismiss = MagicMock()
        event = MagicMock()
        event.button.id = "add"
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(("devbox", None))

    def test_cancel_button(self):
        screen = ManualHostScreen()
        screen.dismiss = MagicMock()
        event = MagicMock()
        event.button.id = "cancel-dialog"
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(None)

    def test_action_cancel_dismisses_none(self):
        screen = ManualHostScreen()
        screen.dismiss = MagicMock()
        screen.action_cancel()
        screen.dismiss.assert_called_once_with(None)


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
        infos = [HostInfo(name="a", has_tmux=True, has_fzf=True)]
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = infos
            result = pick_hosts(infos)
        assert result == infos
        MockApp.assert_called_once_with(infos)

    def test_returns_empty_when_cancelled(self):
        infos = [HostInfo(name="a", has_tmux=True, has_fzf=True)]
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = None
            result = pick_hosts(infos)
        assert result == []

    def test_returns_empty_when_none_selected(self):
        infos = [HostInfo(name="a", has_tmux=True, has_fzf=True)]
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = []
            result = pick_hosts(infos)
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


# ---------------------------------------------------------------------------
# Async Textual tests (run_test) for compose / mount / button coverage
# ---------------------------------------------------------------------------


class TestSessionPickerAsync:
    @pytest.mark.asyncio
    async def test_on_mount_focuses_option_list(self):
        app = SessionPicker(["main", "work"], "devbox")
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            assert ol.has_focus


class TestProfilePickerAsync:
    @pytest.mark.asyncio
    async def test_on_mount_focuses_selection_list(self):
        app = ProfilePicker(["a tmux", "b tmux"])
        async with app.run_test() as pilot:
            sl = app.query_one(SelectionList)
            assert sl.has_focus


class TestHostPickerAsync:
    @staticmethod
    def _eligible(name: str = "alpha") -> HostInfo:
        return HostInfo(name=name, platform="Linux", ip="1.2.3.4",
                        auth="key", has_tmux=True, has_fzf=True)

    @staticmethod
    def _unavailable(name: str = "beta") -> HostInfo:
        return HostInfo(name=name, platform="Linux", has_tmux=False, has_fzf=False)

    @pytest.mark.asyncio
    async def test_compose_mounts_widgets(self):
        app = HostPicker([self._eligible()])
        async with app.run_test() as pilot:
            assert app.query_one("#host-list", SelectionList) is not None
            assert app.query_one("#view-label", Static) is not None

    @pytest.mark.asyncio
    async def test_compose_with_unavailable_section(self):
        app = HostPicker([self._eligible(), self._unavailable()])
        async with app.run_test() as pilot:
            unavail = app.query_one("#unavailable", Static)
            assert unavail is not None

    @pytest.mark.asyncio
    async def test_on_mount_populates_selection_list(self):
        app = HostPicker([self._eligible("alpha")])
        async with app.run_test() as pilot:
            sl = app.query_one("#host-list", SelectionList)
            assert sl.option_count == 1

    @pytest.mark.asyncio
    async def test_cycle_view_updates_unavailable(self):
        app = HostPicker([self._eligible(), self._unavailable()])
        async with app.run_test() as pilot:
            await pilot.press("v")
            assert app._view == 1
            unavail = app.query_one("#unavailable", Static)
            assert unavail is not None

    @pytest.mark.asyncio
    async def test_confirm_button(self):
        app = HostPicker([self._eligible("alpha")])
        async with app.run_test() as pilot:
            await pilot.click("#confirm")

    @pytest.mark.asyncio
    async def test_add_host_button_opens_dialog(self):
        app = HostPicker([self._eligible()])
        async with app.run_test() as pilot:
            await pilot.click("#add-host")
            assert len(app.screen_stack) > 1


class TestHostPickerArrowNav:
    @pytest.mark.asyncio
    async def test_left_right_arrows_between_buttons(self):
        e = HostInfo(name="a", platform="Linux", has_tmux=True, has_fzf=True)
        app = HostPicker([e])
        async with app.run_test() as pilot:
            app.query_one("#add-host", Button).focus()
            await pilot.press("right")
            assert app.focused.id == "confirm"
            await pilot.press("left")
            assert app.focused.id == "add-host"

    @pytest.mark.asyncio
    async def test_arrows_ignored_when_selection_list_focused(self):
        e = HostInfo(name="a", platform="Linux", has_tmux=True, has_fzf=True)
        app = HostPicker([e])
        async with app.run_test() as pilot:
            sl = app.query_one("#host-list", SelectionList)
            sl.focus()
            await pilot.press("left")
            assert sl.has_focus


class TestManualHostScreenAsync:
    @pytest.mark.asyncio
    async def test_compose_renders_dialog(self):
        app = HostPicker([HostInfo(name="h", has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            hostname_input = screen.query_one("#hostname", Input)
            assert hostname_input is not None

    @pytest.mark.asyncio
    async def test_up_down_arrows_between_inputs(self):
        app = HostPicker([HostInfo(name="h", has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#hostname", Input).focus()
            await pilot.press("down")
            assert screen.focused.id == "username"
            await pilot.press("up")
            assert screen.focused.id == "hostname"

    @pytest.mark.asyncio
    async def test_left_right_arrows_between_buttons(self):
        app = HostPicker([HostInfo(name="h", has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#add", Button).focus()
            await pilot.press("right")
            assert screen.focused.id == "cancel-dialog"
            await pilot.press("left")
            assert screen.focused.id == "add"

    @pytest.mark.asyncio
    async def test_unrelated_key_on_input_not_intercepted(self):
        app = HostPicker([HostInfo(name="h", has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#hostname", Input).focus()
            await pilot.press("left")
            assert screen.focused.id == "hostname"
