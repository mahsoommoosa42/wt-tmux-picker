"""Interactive TUI pickers using prompt_toolkit."""

from __future__ import annotations

from html import escape as html_escape
from typing import Callable

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, VSplit
from prompt_toolkit.shortcuts import checkboxlist_dialog, radiolist_dialog
from prompt_toolkit.widgets import Frame, Label, RadioList, TextArea


def pick_session(sessions: list[str], host: str) -> str | None:
    """Show a radiolist of tmux session names; return chosen name or None."""
    values = [(s, s) for s in sessions]
    return radiolist_dialog(
        title=f"tmux sessions on {host}",
        text="↑/↓ to move, Enter to select, Escape for plain SSH",
        values=values,
    ).run()


def pick_profiles(profiles: list[str]) -> list[str]:
    """Show a checkboxlist of registered WT profiles; return checked names."""
    values = [(p, p) for p in profiles]
    result = checkboxlist_dialog(
        title="Select profiles to remove",
        text="Space to toggle, Enter to confirm",
        values=values,
    ).run()
    return result or []


def _format_preview(
    info: dict | None,
    pane_content: str,
) -> str:
    """Build the preview text from session metadata and pane content."""
    lines: list[str] = []
    if info is not None:
        lines.append(f"  Windows:   {info['windows']}")
        lines.append(f"  Created:   {info['created']}")
        lines.append(f"  Attached:  {'Yes' if info['attached'] else 'No'}")
        lines.append("")
        lines.append("  --- Pane Content ---")
    if pane_content:
        for line in pane_content.splitlines():
            lines.append(f"  {line}")
    elif info is not None:
        lines.append("  (empty)")
    else:
        lines.append("  (unavailable)")
    return "\n".join(lines)


def pick_session_with_preview(
    sessions: list[str],
    host: str,
    get_info: Callable[[str], dict | None],
    get_pane: Callable[[str], str],
) -> str | None:
    """Show a session picker with a live preview pane.

    *get_info* is called with the session name and should return a metadata
    dict (or None).  *get_pane* is called with the session name and should
    return pane content as a string.

    Returns the selected session name, or None if the user pressed Escape.
    """
    values = [(s, s) for s in sessions]
    radio = RadioList(values)

    # Replace RadioList's internal key bindings so our handlers take
    # priority for enter/up/down (RadioList's _click/_up/_down would
    # otherwise shadow the app-level bindings).
    kb = KeyBindings()

    result_box: list[str | None] = [None]

    preview = TextArea(
        text="",
        read_only=True,
        focusable=False,
        scrollbar=True,
    )

    def _refresh_preview() -> None:
        if radio._selected_index >= len(radio.values):
            preview.text = ""
            return
        current = radio.values[radio._selected_index][0]
        info = get_info(current)
        pane = get_pane(current)
        preview.text = _format_preview(info, pane)

    _refresh_preview()

    @kb.add("enter")
    def _accept(event) -> None:  # type: ignore[no-untyped-def]
        result_box[0] = radio.values[radio._selected_index][0]
        event.app.exit()

    @kb.add("escape")
    def _cancel(event) -> None:  # type: ignore[no-untyped-def]
        result_box[0] = None
        event.app.exit()

    @kb.add("up")
    def _up(event) -> None:  # type: ignore[no-untyped-def]
        radio._selected_index = max(0, radio._selected_index - 1)
        _refresh_preview()

    @kb.add("down")
    def _down(event) -> None:  # type: ignore[no-untyped-def]
        radio._selected_index = min(
            len(radio.values) - 1, radio._selected_index + 1
        )
        _refresh_preview()

    # Override RadioList's control bindings with ours so there is no
    # conflict between the control-level and app-level handlers.
    radio.control.key_bindings = kb

    body = VSplit(
        [
            Frame(radio, title="Sessions"),
            Frame(preview, title="Preview"),
        ],
        padding=1,
    )

    safe_host = html_escape(host)
    layout = Layout(
        HSplit(
            [
                Label(HTML(f"  <b>tmux sessions on {safe_host}</b>")),
                body,
                Label("  ↑/↓ move  Enter select  Escape plain SSH"),
            ]
        )
    )

    app: Application[None] = Application(
        layout=layout,
        full_screen=True,
    )
    app.run()

    return result_box[0]
