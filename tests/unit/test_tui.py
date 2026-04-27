"""Unit tests for tui.py."""

from unittest.mock import MagicMock, patch

from prompt_toolkit.keys import Keys

from wt_tmux_picker.tui import (
    _format_preview,
    pick_profiles,
    pick_session,
    pick_session_with_preview,
)


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


class TestFormatPreview:
    def test_with_info_and_content(self):
        info = {
            "name": "main",
            "windows": 3,
            "created": "2023-11-14 12:30:00 UTC",
            "attached": True,
        }
        result = _format_preview(info, "$ ls\nfile1")
        assert "Windows:   3" in result
        assert "2023-11-14" in result
        assert "Yes" in result
        assert "$ ls" in result
        assert "file1" in result

    def test_with_info_no_content(self):
        info = {
            "name": "work",
            "windows": 1,
            "created": "2024-01-01 00:00:00 UTC",
            "attached": False,
        }
        result = _format_preview(info, "")
        assert "No" in result
        assert "(empty)" in result

    def test_no_info_no_content(self):
        result = _format_preview(None, "")
        assert "(unavailable)" in result

    def test_no_info_with_content(self):
        result = _format_preview(None, "$ pwd\n/home")
        assert "$ pwd" in result
        assert "/home" in result


def _patches():
    """Context managers to mock prompt_toolkit widgets for preview tests."""
    return (
        patch("wt_tmux_picker.tui.RadioList"),
        patch("wt_tmux_picker.tui.TextArea"),
        patch("wt_tmux_picker.tui.Frame"),
        patch("wt_tmux_picker.tui.VSplit"),
        patch("wt_tmux_picker.tui.HSplit"),
        patch("wt_tmux_picker.tui.Layout"),
        patch("wt_tmux_picker.tui.Label"),
        patch("wt_tmux_picker.tui.HTML"),
    )


def _make_radio(current_value, values):
    mock_radio = MagicMock()
    mock_radio.current_value = current_value
    mock_radio.values = values
    mock_radio._selected_index = 0
    return mock_radio


_KEY_MAP = {
    "enter": (Keys.ControlM,),
    "escape": (Keys.Escape,),
    "up": (Keys.Up,),
    "down": (Keys.Down,),
}


def _get_handlers(mock_app_cls):
    kb = mock_app_cls.call_args.kwargs["key_bindings"]
    handlers = {}
    for b in kb.bindings:
        for name, keys in _KEY_MAP.items():
            if tuple(b.keys) == keys:
                handlers[name] = b.handler
    return handlers


class TestPickSessionWithPreview:
    def test_returns_selected_session(self):
        mock_radio = _make_radio("main", [("main", "main"), ("work", "work")])
        mock_app = MagicMock()

        (p_radio, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html) = _patches()
        with p_radio as mr, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html:
            mr.return_value = mock_radio
            with patch("wt_tmux_picker.tui.Application", return_value=mock_app) as mock_cls:

                def run_side_effect():
                    h = _get_handlers(mock_cls)
                    h["enter"](MagicMock())

                mock_app.run.side_effect = run_side_effect
                result = pick_session_with_preview(
                    ["main", "work"],
                    "devbox",
                    get_info=lambda s: {"name": s, "windows": 1, "created": "now", "attached": False},
                    get_pane=lambda s: "$ ls",
                )
        assert result == "main"

    def test_returns_none_on_escape(self):
        mock_radio = _make_radio("main", [("main", "main")])
        mock_app = MagicMock()

        (p_radio, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html) = _patches()
        with p_radio as mr, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html:
            mr.return_value = mock_radio
            with patch("wt_tmux_picker.tui.Application", return_value=mock_app) as mock_cls:

                def run_side_effect():
                    h = _get_handlers(mock_cls)
                    h["escape"](MagicMock())

                mock_app.run.side_effect = run_side_effect
                result = pick_session_with_preview(
                    ["main"],
                    "devbox",
                    get_info=lambda s: None,
                    get_pane=lambda s: "",
                )
        assert result is None

    def test_up_and_down_keys(self):
        mock_radio = _make_radio("main", [("main", "main"), ("work", "work")])
        mock_app = MagicMock()

        (p_radio, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html) = _patches()
        with p_radio as mr, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html:
            mr.return_value = mock_radio
            with patch("wt_tmux_picker.tui.Application", return_value=mock_app) as mock_cls:

                def run_side_effect():
                    h = _get_handlers(mock_cls)
                    ev = MagicMock()
                    h["down"](ev)
                    h["up"](ev)
                    h["escape"](ev)

                mock_app.run.side_effect = run_side_effect
                result = pick_session_with_preview(
                    ["main", "work"],
                    "devbox",
                    get_info=lambda s: {"name": s, "windows": 1, "created": "now", "attached": False},
                    get_pane=lambda s: "content",
                )
        assert result is None

    def test_out_of_range_index_clears_preview(self):
        mock_radio = _make_radio("main", [("main", "main")])
        mock_radio._selected_index = 5  # out of range
        mock_app = MagicMock()

        (p_radio, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html) = _patches()
        with p_radio as mr, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html:
            mr.return_value = mock_radio
            with patch("wt_tmux_picker.tui.Application", return_value=mock_app) as mock_cls:

                def run_side_effect():
                    h = _get_handlers(mock_cls)
                    h["escape"](MagicMock())

                mock_app.run.side_effect = run_side_effect
                result = pick_session_with_preview(
                    ["main"],
                    "devbox",
                    get_info=lambda s: None,
                    get_pane=lambda s: "",
                )
        assert result is None

    def test_enter_returns_navigated_session(self):
        mock_radio = _make_radio("main", [("main", "main"), ("work", "work")])
        mock_app = MagicMock()

        (p_radio, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html) = _patches()
        with p_radio as mr, p_ta, p_frame, p_vs, p_hs, p_layout, p_label, p_html:
            mr.return_value = mock_radio
            with patch("wt_tmux_picker.tui.Application", return_value=mock_app) as mock_cls:

                def run_side_effect():
                    h = _get_handlers(mock_cls)
                    h["down"](MagicMock())
                    h["enter"](MagicMock())

                mock_app.run.side_effect = run_side_effect
                result = pick_session_with_preview(
                    ["main", "work"],
                    "devbox",
                    get_info=lambda s: {"name": s, "windows": 1, "created": "now", "attached": False},
                    get_pane=lambda s: "$ ls",
                )
        assert result == "work"
