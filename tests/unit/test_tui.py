"""Unit tests for tui.py."""

import pytest
from unittest.mock import MagicMock, patch

from textual.widgets import Button, Input, OptionList, SelectionList, Static
from textual.worker import WorkerState

from wt_tmux_picker.host_info import HostInfo
from wt_tmux_picker.tui import (
    _CAPTURE_PREFIX,
    _PREVIEW_EMPTY,
    _PREVIEW_LOADING,
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
        assert app._capture is None

    def test_compose_without_capture_yields_four_widgets(self):
        app = SessionPicker(["a", "b"], "host")
        widgets = list(app.compose())
        assert len(widgets) == 4

    def test_init_with_capture_stores_callable(self):
        cap = lambda s: ""  # noqa: E731
        app = SessionPicker(["a"], "host", capture=cap)
        assert app._capture is cap

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

    def test_highlighted_without_capture_is_noop(self):
        app = SessionPicker(["main"], "host")
        app._request_preview = MagicMock()
        event = MagicMock()
        event.option.id = "main"
        app.on_option_list_option_highlighted(event)
        app._request_preview.assert_not_called()

    def test_highlighted_with_none_id_ignored(self):
        app = SessionPicker(["main"], "host", capture=lambda s: "")
        app._request_preview = MagicMock()
        event = MagicMock()
        event.option.id = None
        app.on_option_list_option_highlighted(event)
        app._request_preview.assert_not_called()

    def test_highlighted_with_capture_requests_preview(self):
        app = SessionPicker(["main"], "host", capture=lambda s: "")
        app._request_preview = MagicMock()
        event = MagicMock()
        event.option.id = "main"
        app.on_option_list_option_highlighted(event)
        app._request_preview.assert_called_once_with("main")

    def test_request_preview_sets_loading_and_runs_worker(self):
        cap = MagicMock(return_value="hello")
        app = SessionPicker(["main"], "host", capture=cap)
        title_static = MagicMock()
        body_static = MagicMock()

        def fake_query_one(selector, _cls):
            return title_static if selector == "#preview-title" else body_static

        app.query_one = fake_query_one
        app.run_worker = MagicMock()
        app._request_preview("main")
        assert app._pending_session == "main"
        title_static.update.assert_called_once_with("Preview: main")
        body_static.update.assert_called_once_with(_PREVIEW_LOADING)
        app.run_worker.assert_called_once()
        kwargs = app.run_worker.call_args.kwargs
        assert kwargs["name"] == f"{_CAPTURE_PREFIX}main"
        assert kwargs["exclusive"] is True
        assert kwargs["thread"] is True
        # Worker callable should invoke the capture function.
        worker_fn = app.run_worker.call_args.args[0]
        assert worker_fn() == "hello"
        cap.assert_called_with("main")

    def _capture_event(self, name, state, result=""):
        worker = MagicMock()
        worker.name = name
        worker.result = result
        event = MagicMock()
        event.worker = worker
        event.state = state
        return event

    def test_worker_state_changed_ignores_other_workers(self):
        app = SessionPicker(["main"], "host", capture=lambda s: "")
        app.query_one = MagicMock()
        event = self._capture_event("other", WorkerState.SUCCESS, "x")
        app.on_worker_state_changed(event)
        app.query_one.assert_not_called()

    def test_worker_state_changed_ignores_unknown_none_name(self):
        app = SessionPicker(["main"], "host", capture=lambda s: "")
        app.query_one = MagicMock()
        # Worker with name=None must not raise.
        event = self._capture_event(None, WorkerState.SUCCESS, "x")
        app.on_worker_state_changed(event)
        app.query_one.assert_not_called()

    def test_worker_state_changed_ignores_non_success(self):
        app = SessionPicker(["main"], "host", capture=lambda s: "")
        app._pending_session = "main"
        app.query_one = MagicMock()
        event = self._capture_event(
            f"{_CAPTURE_PREFIX}main", WorkerState.RUNNING, "x",
        )
        app.on_worker_state_changed(event)
        app.query_one.assert_not_called()

    def test_worker_state_changed_stale_session_ignored(self):
        app = SessionPicker(["main", "work"], "host", capture=lambda s: "")
        app._pending_session = "work"
        app.query_one = MagicMock()
        event = self._capture_event(
            f"{_CAPTURE_PREFIX}main", WorkerState.SUCCESS, "stale",
        )
        app.on_worker_state_changed(event)
        app.query_one.assert_not_called()

    def test_worker_state_changed_updates_preview(self):
        app = SessionPicker(["main"], "host", capture=lambda s: "")
        app._pending_session = "main"
        static = MagicMock()
        app.query_one = MagicMock(return_value=static)
        event = self._capture_event(
            f"{_CAPTURE_PREFIX}main", WorkerState.SUCCESS, "live text",
        )
        app.on_worker_state_changed(event)
        static.update.assert_called_once_with("live text")

    def test_worker_state_changed_empty_shows_placeholder(self):
        app = SessionPicker(["main"], "host", capture=lambda s: "")
        app._pending_session = "main"
        static = MagicMock()
        app.query_one = MagicMock(return_value=static)
        event = self._capture_event(
            f"{_CAPTURE_PREFIX}main", WorkerState.SUCCESS, "",
        )
        app.on_worker_state_changed(event)
        static.update.assert_called_once_with(_PREVIEW_EMPTY)

    def test_worker_state_changed_none_result_shows_placeholder(self):
        app = SessionPicker(["main"], "host", capture=lambda s: "")
        app._pending_session = "main"
        static = MagicMock()
        app.query_one = MagicMock(return_value=static)
        event = self._capture_event(
            f"{_CAPTURE_PREFIX}main", WorkerState.SUCCESS, None,
        )
        app.on_worker_state_changed(event)
        static.update.assert_called_once_with(_PREVIEW_EMPTY)


class TestHostPicker:
    @staticmethod
    def _eligible(name: str = "alpha") -> HostInfo:
        return HostInfo(name=name, platform="Linux", auth="key",
                        has_tmux=True, has_fzf=True)

    @staticmethod
    def _unavailable(name: str = "beta", tmux: bool = False) -> HostInfo:
        return HostInfo(name=name, platform="Linux", auth="key",
                        has_tmux=tmux, has_fzf=False)

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

    def test_on_manual_host_starts_worker(self):
        app = HostPicker([self._eligible()])
        app.run_worker = MagicMock()
        app.notify = MagicMock()
        app._on_manual_host(("newhost", "alice", None))
        app.run_worker.assert_called_once()
        app.notify.assert_called_once()

    def _make_worker_event(self, name, state, result=None):
        worker = MagicMock()
        worker.name = name
        worker.result = result
        event = MagicMock()
        event.worker = worker
        event.state = state
        return event

    def test_worker_success_eligible_adds_to_manual(self):
        app = HostPicker([self._eligible()])
        mock_sl = MagicMock()
        mock_sl.selected = set()
        mock_sl.option_count = 1
        mock_sl.get_option_at_index.return_value = MagicMock(value="alpha")
        app.query_one = MagicMock(return_value=mock_sl)
        app.notify = MagicMock()
        info = HostInfo(name="newhost", user="alice", platform="Linux",
                        ip="1.2.3.4", auth="key", has_tmux=True, has_fzf=True)
        event = self._make_worker_event("probe_manual", WorkerState.SUCCESS, info)
        app.on_worker_state_changed(event)
        assert len(app._manual) == 1
        assert app._manual[0].manual is True
        app.notify.assert_called_once()

    def test_worker_success_ineligible_rejects(self):
        app = HostPicker([self._eligible()])
        app.notify = MagicMock()
        app.query = MagicMock(return_value=MagicMock(__bool__=lambda s: False))
        app.mount = MagicMock()
        app.query_one = MagicMock()
        info = HostInfo(name="badhost", platform="Linux", auth="key",
                        has_tmux=False, has_fzf=False)
        event = self._make_worker_event("probe_manual", WorkerState.SUCCESS, info)
        app.on_worker_state_changed(event)
        assert len(app._unavailable) == 1  # newly rejected
        assert app._manual == []
        app.mount.assert_called_once()

    def test_worker_success_ineligible_windows_message(self):
        app = HostPicker([self._eligible()])
        app.notify = MagicMock()
        app.query = MagicMock(return_value=MagicMock(__bool__=lambda s: False))
        app.mount = MagicMock()
        app.query_one = MagicMock()
        info = HostInfo(name="winbox", platform="Windows", auth="key")
        event = self._make_worker_event("probe_manual", WorkerState.SUCCESS, info)
        app.on_worker_state_changed(event)
        call_args = app.notify.call_args
        assert "Windows" in call_args[0][0]
        assert "tmux not supported" in call_args[0][0]

    def test_worker_success_updates_existing_unavailable(self):
        e = self._eligible()
        u = self._unavailable()
        app = HostPicker([e, u])
        app.notify = MagicMock()
        mock_unavail = MagicMock()
        mock_result_set = MagicMock(__bool__=lambda s: True)
        mock_result_set.first.return_value = mock_unavail
        app.query = MagicMock(return_value=mock_result_set)
        info = HostInfo(name="bad2", platform="Linux", auth="key",
                        has_tmux=False, has_fzf=True)
        event = self._make_worker_event("probe_manual", WorkerState.SUCCESS, info)
        app.on_worker_state_changed(event)
        mock_unavail.update.assert_called_once()

    def test_worker_wrong_name_ignored(self):
        app = HostPicker([self._eligible()])
        event = self._make_worker_event("other_worker", WorkerState.SUCCESS)
        app.on_worker_state_changed(event)  # should not raise

    def test_worker_non_success_ignored(self):
        app = HostPicker([self._eligible()])
        event = self._make_worker_event("probe_manual", WorkerState.RUNNING)
        app.on_worker_state_changed(event)  # should not raise

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
        u = HostInfo(name="bad", platform="Linux", auth="key",
                    has_tmux=False, has_fzf=False)
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
        mock_keyfile = MagicMock()
        mock_keyfile.value = "~/.ssh/id_rsa"

        def fake_query_one(selector, cls):
            if selector == "#hostname":
                return mock_hostname
            if selector == "#username":
                return mock_username
            return mock_keyfile

        screen.query_one = fake_query_one
        screen.dismiss = MagicMock()
        event = MagicMock()
        event.button.id = "add"
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(("devbox", "alice", "~/.ssh/id_rsa"))

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
        mock_keyfile = MagicMock()
        mock_keyfile.value = ""

        def fake_query_one(selector, cls):
            if selector == "#hostname":
                return mock_hostname
            if selector == "#username":
                return mock_username
            return mock_keyfile

        screen.query_one = fake_query_one
        screen.dismiss = MagicMock()
        event = MagicMock()
        event.button.id = "add"
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(("devbox", None, None))

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
        MockApp.assert_called_once_with(
            ["main", "work"], "devbox", capture=None,
        )

    def test_returns_none_when_cancelled(self):
        with patch("wt_tmux_picker.tui.SessionPicker") as MockApp:
            MockApp.return_value.run.return_value = None
            result = pick_session(["main"], "devbox")
        assert result is None

    def test_passes_capture_callable(self):
        cap = MagicMock(return_value="hello")
        with patch("wt_tmux_picker.tui.SessionPicker") as MockApp:
            MockApp.return_value.run.return_value = "main"
            pick_session(["main"], "devbox", capture=cap)
        MockApp.assert_called_once_with(["main"], "devbox", capture=cap)


class TestPickHosts:
    def test_returns_selected_hosts(self):
        infos = [HostInfo(name="a", auth="key", has_tmux=True, has_fzf=True)]
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = infos
            result = pick_hosts(infos)
        assert result == infos
        MockApp.assert_called_once_with(infos)

    def test_returns_empty_when_cancelled(self):
        infos = [HostInfo(name="a", auth="key", has_tmux=True, has_fzf=True)]
        with patch("wt_tmux_picker.tui.HostPicker") as MockApp:
            MockApp.return_value.run.return_value = None
            result = pick_hosts(infos)
        assert result == []

    def test_returns_empty_when_none_selected(self):
        infos = [HostInfo(name="a", auth="key", has_tmux=True, has_fzf=True)]
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

    @pytest.mark.asyncio
    async def test_on_mount_with_capture_requests_initial_preview(self):
        captured: list[str] = []

        def cap(name: str) -> str:
            captured.append(name)
            return f"preview-of-{name}"

        app = SessionPicker(["main", "work"], "devbox", capture=cap)
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
            # Either on_mount or the auto-highlight (or both, dedup'd by the
            # exclusive worker) triggers at least one capture of "main".
            assert captured
            assert all(name == "main" for name in captured)
            assert app._pending_session == "main"
            # Preview pane is mounted when capture is supplied.
            assert app.query_one("#preview", Static) is not None
            assert app.query_one("#preview-title", Static) is not None

    @pytest.mark.asyncio
    async def test_on_mount_with_capture_empty_sessions_skips_preview(self):
        cap = MagicMock()
        app = SessionPicker([], "devbox", capture=cap)
        async with app.run_test() as pilot:
            await pilot.pause()
        cap.assert_not_called()


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
        e = HostInfo(name="a", platform="Linux", auth="key",
                    has_tmux=True, has_fzf=True)
        app = HostPicker([e])
        async with app.run_test() as pilot:
            app.query_one("#add-host", Button).focus()
            await pilot.press("right")
            assert app.focused.id == "confirm"
            await pilot.press("left")
            assert app.focused.id == "add-host"

    @pytest.mark.asyncio
    async def test_arrows_ignored_when_selection_list_focused(self):
        e = HostInfo(name="a", platform="Linux", auth="key",
                    has_tmux=True, has_fzf=True)
        app = HostPicker([e])
        async with app.run_test() as pilot:
            sl = app.query_one("#host-list", SelectionList)
            sl.focus()
            await pilot.press("left")
            assert sl.has_focus


    @pytest.mark.asyncio
    async def test_left_from_first_button_stays(self):
        e = HostInfo(name="a", platform="Linux", auth="key",
                    has_tmux=True, has_fzf=True)
        app = HostPicker([e])
        async with app.run_test() as pilot:
            app.query_one("#add-host", Button).focus()
            await pilot.press("left")
            assert app.focused.id == "add-host"

    @pytest.mark.asyncio
    async def test_right_from_last_button_stays(self):
        e = HostInfo(name="a", platform="Linux", auth="key",
                    has_tmux=True, has_fzf=True)
        app = HostPicker([e])
        async with app.run_test() as pilot:
            app.query_one("#confirm", Button).focus()
            await pilot.press("right")
            assert app.focused.id == "confirm"


class TestHostPickerVerticalNav:
    @pytest.mark.asyncio
    async def test_up_from_button_focuses_list(self):
        e = HostInfo(name="a", platform="Linux", auth="key",
                    has_tmux=True, has_fzf=True)
        app = HostPicker([e])
        async with app.run_test() as pilot:
            app.query_one("#add-host", Button).focus()
            await pilot.press("up")
            assert app.query_one("#host-list", SelectionList).has_focus

    @pytest.mark.asyncio
    async def test_down_from_last_list_item_focuses_button(self):
        e = HostInfo(name="a", platform="Linux", auth="key",
                    has_tmux=True, has_fzf=True)
        app = HostPicker([e])
        async with app.run_test() as pilot:
            sl = app.query_one("#host-list", SelectionList)
            sl.focus()
            sl.highlighted = sl.option_count - 1
            await pilot.press("down")
            assert isinstance(app.focused, Button)


class TestProfilePickerNav:
    @pytest.mark.asyncio
    async def test_up_from_button_focuses_list(self):
        app = ProfilePicker(["a tmux"])
        async with app.run_test() as pilot:
            app.query_one("#confirm", Button).focus()
            await pilot.press("up")
            assert app.query_one(SelectionList).has_focus

    @pytest.mark.asyncio
    async def test_down_from_last_list_item_focuses_button(self):
        app = ProfilePicker(["a tmux"])
        async with app.run_test() as pilot:
            sl = app.query_one(SelectionList)
            sl.focus()
            sl.highlighted = sl.option_count - 1
            await pilot.press("down")
            assert app.query_one("#confirm", Button).has_focus


    @pytest.mark.asyncio
    async def test_unhandled_key_passes_through(self):
        app = ProfilePicker(["a tmux"])
        async with app.run_test() as pilot:
            sl = app.query_one(SelectionList)
            sl.focus()
            await pilot.press("left")
            assert sl.has_focus


class TestManualHostScreenAsync:
    @pytest.mark.asyncio
    async def test_compose_renders_dialog(self):
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            hostname_input = screen.query_one("#hostname", Input)
            assert hostname_input is not None

    @pytest.mark.asyncio
    async def test_up_down_arrows_between_inputs(self):
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
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
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
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
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#hostname", Input).focus()
            await pilot.press("left")
            assert screen.focused.id == "hostname"

    @pytest.mark.asyncio
    async def test_down_from_last_input_focuses_add_button(self):
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#keyfile", Input).focus()
            await pilot.press("down")
            assert screen.focused.id == "add"

    @pytest.mark.asyncio
    async def test_up_from_button_focuses_last_input(self):
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#add", Button).focus()
            await pilot.press("up")
            assert screen.focused.id == "keyfile"

    @pytest.mark.asyncio
    async def test_up_from_first_input_stays(self):
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#hostname", Input).focus()
            await pilot.press("up")
            assert screen.focused.id == "hostname"

    @pytest.mark.asyncio
    async def test_left_from_first_button_stays(self):
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#add", Button).focus()
            await pilot.press("left")
            assert screen.focused.id == "add"

    @pytest.mark.asyncio
    async def test_right_from_last_button_stays(self):
        app = HostPicker([HostInfo(name="h", auth="key",
                                      has_tmux=True, has_fzf=True)])
        async with app.run_test() as pilot:
            app.push_screen(ManualHostScreen(), callback=app._on_manual_host)
            await pilot.pause()
            screen = app.screen_stack[-1]
            screen.query_one("#cancel-dialog", Button).focus()
            await pilot.press("right")
            assert screen.focused.id == "cancel-dialog"
