"""Interactive TUI pickers using Textual."""

from __future__ import annotations

from typing import Callable

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, OptionList, SelectionList, Static
from textual.widgets.option_list import Option
from textual.worker import Worker, WorkerState

from .host_info import HostInfo, _VIEW_COUNT, probe_host


_PREVIEW_LOADING = "Loading preview\u2026"
_PREVIEW_EMPTY = "(no preview available)"
_CAPTURE_PREFIX = "capture:"


class SessionPicker(App[str | None]):
    """Single-select picker for tmux session names with a live preview.

    When *capture* is provided, the right-hand pane shows a snapshot of
    the highlighted session's active pane, refreshed as the user
    navigates. The capture runs in a background thread worker so the UI
    stays responsive; rapid navigation cancels in-flight captures.
    """

    CSS = """
    #info { padding: 1 2; color: $text-muted; }
    #session-list { height: 1fr; margin: 0 2; }
    #main { height: 1fr; }
    #main #session-list { width: 40%; margin: 0 0 0 2; }
    #preview-box {
        width: 1fr;
        margin: 0 2 0 1;
        border: round $accent;
        padding: 0 1;
    }
    #preview-title { color: $accent; height: 1; }
    #preview-scroll { height: 1fr; }
    #preview { width: 1fr; }
    """
    BINDINGS = [("escape", "cancel", "Plain SSH")]

    def __init__(
        self,
        sessions: list[str],
        host: str,
        capture: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__()
        self.sessions = sessions
        self.host = host
        self._capture = capture
        self._pending_session: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        hint = (
            "\u2191/\u2193 arrow keys to move, Enter to select, "
            "Escape for plain SSH"
        )
        if self._capture is not None:
            hint += " \u2014 preview updates as you move"
        yield Static(f"tmux sessions on {self.host}\n{hint}", id="info")
        if self._capture is None:
            yield OptionList(
                *[Option(s, id=s) for s in self.sessions], id="session-list",
            )
        else:
            with Horizontal(id="main"):
                yield OptionList(
                    *[Option(s, id=s) for s in self.sessions],
                    id="session-list",
                )
                with Vertical(id="preview-box"):
                    yield Static("Preview", id="preview-title")
                    with VerticalScroll(id="preview-scroll"):
                        yield Static("", id="preview")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#session-list", OptionList).focus()
        if self._capture is not None and self.sessions:
            self._request_preview(self.sessions[0])

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.exit(str(event.option.id))

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if self._capture is None:
            return
        opt_id = event.option.id
        if opt_id is None:
            return
        self._request_preview(str(opt_id))

    def action_cancel(self) -> None:
        self.exit(None)

    # -- preview helpers ----------------------------------------------------

    def _request_preview(self, session: str) -> None:
        self._pending_session = session
        self.query_one("#preview-title", Static).update(f"Preview: {session}")
        self.query_one("#preview", Static).update(_PREVIEW_LOADING)
        capture = self._capture
        assert capture is not None
        self.run_worker(
            lambda s=session: capture(s),
            name=f"{_CAPTURE_PREFIX}{session}",
            exclusive=True,
            thread=True,
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        name = event.worker.name or ""
        if not name.startswith(_CAPTURE_PREFIX):
            return
        if event.state != WorkerState.SUCCESS:
            return
        session = name[len(_CAPTURE_PREFIX):]
        if session != self._pending_session:
            return
        output = event.worker.result or ""
        self.query_one("#preview", Static).update(output or _PREVIEW_EMPTY)


# ---------------------------------------------------------------------------
# Manual host entry dialog
# ---------------------------------------------------------------------------

class ManualHostScreen(ModalScreen[tuple[str, str | None, str | None] | None]):
    """Modal dialog for entering a hostname, optional username, and key file."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    CSS = """
    ManualHostScreen {
        align: center middle;
    }
    #dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        border: thick $accent;
        background: $surface;
    }
    #dialog Static { margin: 1 0 0 0; }
    #dialog Input { margin: 0 0 1 0; }
    #btn-bar { height: 3; margin: 1 0 0 0; }
    """

    _INPUT_ORDER = ("hostname", "username", "keyfile")

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Hostname:")
            yield Input(placeholder="e.g. devbox.example.com", id="hostname")
            yield Static("Username (optional):")
            yield Input(placeholder="e.g. alice", id="username")
            yield Static("Key file (optional):")
            yield Input(placeholder="e.g. ~/.ssh/id_ed25519", id="keyfile")
            with Horizontal(id="btn-bar"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Cancel", id="cancel-dialog")

    def on_mount(self) -> None:
        self.query_one("#hostname", Input).focus()

    def on_key(self, event: Key) -> None:
        focused = self.focused
        if isinstance(focused, Input) and event.key in ("up", "down"):
            event.prevent_default()
            event.stop()
            idx = self._INPUT_ORDER.index(focused.id or "")
            if event.key == "down":
                if idx < len(self._INPUT_ORDER) - 1:
                    self.query_one(f"#{self._INPUT_ORDER[idx + 1]}", Input).focus()
                else:
                    self.query_one("#add", Button).focus()
            else:
                if idx > 0:
                    self.query_one(f"#{self._INPUT_ORDER[idx - 1]}", Input).focus()
        elif isinstance(focused, Button) and event.key in ("left", "right"):
            event.prevent_default()
            event.stop()
            buttons = list(self.query(Button))
            idx = buttons.index(focused)
            if event.key == "right" and idx < len(buttons) - 1:
                buttons[idx + 1].focus()
            elif event.key == "left" and idx > 0:
                buttons[idx - 1].focus()
        elif isinstance(focused, Button) and event.key == "up":
            event.prevent_default()
            event.stop()
            self.query_one(f"#{self._INPUT_ORDER[-1]}", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            hostname = self.query_one("#hostname", Input).value.strip()
            if not hostname:
                return
            raw_user = self.query_one("#username", Input).value.strip()
            raw_key = self.query_one("#keyfile", Input).value.strip()
            self.dismiss((hostname, raw_user or None, raw_key or None))
        else:
            self.dismiss(None)


# ---------------------------------------------------------------------------
# Host picker (setup flow)
# ---------------------------------------------------------------------------

_VIEW_NAMES = [
    "Name + Platform",
    "Name + Platform + IP",
    "Name + Platform + IP + Auth",
]


class HostPicker(App[list[HostInfo]]):
    """Multi-select picker for SSH hosts during setup."""

    CSS = """
    #info { padding: 1 2; color: $text-muted; }
    #view-label { padding: 0 2; color: $accent; }
    SelectionList { height: 1fr; margin: 0 2; }
    #unavailable { padding: 1 2; color: $error; }
    #btn-bar { height: 3; margin: 1 2; }
    """
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("v", "cycle_view", "Cycle View"),
    ]

    def __init__(self, hosts: list[HostInfo]) -> None:
        super().__init__()
        self.hosts = hosts
        self._eligible = [h for h in hosts if h.eligible]
        self._unavailable = [h for h in hosts if not h.eligible]
        self._manual: list[HostInfo] = []
        self._view = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Select SSH hosts to set up\n"
            "\u2191/\u2193 to move, Space to toggle, [v] cycle view, Escape to cancel",
            id="info",
        )
        yield Static(f"View: {_VIEW_NAMES[0]}", id="view-label")
        yield SelectionList[str](id="host-list")
        if self._unavailable:
            yield Static(self._unavailable_text(), id="unavailable")
        with Horizontal(id="btn-bar"):
            yield Button("Add Host\u2026", id="add-host")
            yield Button("Confirm", variant="primary", id="confirm")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_selection_list()
        self.query_one("#host-list", SelectionList).focus()

    def on_key(self, event: Key) -> None:
        focused = self.focused
        if isinstance(focused, Button) and event.key in ("left", "right"):
            event.prevent_default()
            event.stop()
            buttons = list(self.query("#btn-bar Button"))
            idx = buttons.index(focused)
            if event.key == "right" and idx < len(buttons) - 1:
                buttons[idx + 1].focus()
            elif event.key == "left" and idx > 0:
                buttons[idx - 1].focus()
        elif isinstance(focused, Button) and event.key == "up":
            event.prevent_default()
            event.stop()
            self.query_one("#host-list", SelectionList).focus()
        elif isinstance(focused, SelectionList) and event.key == "down":
            event.prevent_default()
            event.stop()
            self.query_one("#add-host", Button).focus()

    # -- actions ------------------------------------------------------------

    def action_cycle_view(self) -> None:
        self._view = (self._view + 1) % _VIEW_COUNT
        self.query_one("#view-label", Static).update(
            f"View: {_VIEW_NAMES[self._view]}"
        )
        self._refresh_selection_list()
        unavail_nodes = self.query("#unavailable")
        if unavail_nodes:
            unavail_nodes.first(Static).update(self._unavailable_text())

    def action_cancel(self) -> None:
        self.exit([])

    # -- events -------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-host":
            self.push_screen(ManualHostScreen(), callback=self._on_manual_host)
        elif event.button.id == "confirm":
            self._confirm()

    def _on_manual_host(
        self, result: tuple[str, str | None, str | None] | None,
    ) -> None:
        if result is None:
            return
        hostname, username, keyfile = result
        self.notify(f"Probing {hostname}\u2026")
        self.run_worker(
            lambda: probe_host(hostname, username, identity_file=keyfile),
            name="probe_manual",
            exclusive=True,
            thread=True,
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "probe_manual":
            return
        if event.state != WorkerState.SUCCESS:
            return
        info: HostInfo = event.worker.result
        info.manual = True
        if info.eligible:
            self._manual.append(info)
            self._refresh_selection_list()
            self.notify(f"{info.name} added")
        else:
            self._unavailable.append(info)
            unavail_nodes = self.query("#unavailable")
            text = self._unavailable_text()
            if unavail_nodes:
                unavail_nodes.first(Static).update(text)
            else:
                self.mount(Static(text, id="unavailable"),
                           before=self.query_one("#btn-bar"))
            self.notify(
                f"{info.name} rejected \u2014 {info.rejection_reason}",
                severity="error",
            )

    def _confirm(self) -> None:
        sl = self.query_one("#host-list", SelectionList)
        selected_names: set[str] = set(sl.selected)
        all_hosts = self._eligible + self._manual
        chosen = [h for h in all_hosts if h.name in selected_names]
        self.exit(chosen)

    # -- helpers ------------------------------------------------------------

    def _refresh_selection_list(self) -> None:
        sl = self.query_one("#host-list", SelectionList)
        selected: set[str] = set(sl.selected)
        first_load = sl.option_count == 0
        known: set[str] = {sl.get_option_at_index(i).value
                           for i in range(sl.option_count)}
        sl.clear_options()
        for info in self._eligible + self._manual:
            label = info.label(self._view)
            if first_load or info.name not in known:
                checked = True
            else:
                checked = info.name in selected
            sl.add_option((label, info.name, checked))

    def _unavailable_text(self) -> str:
        lines = [
            f"  {h.unavailable_label(self._view)}"
            for h in self._unavailable
        ]
        return "Unavailable:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Profile picker (cleanup flow)
# ---------------------------------------------------------------------------

class ProfilePicker(App[list[str]]):
    """Multi-select picker for WT profile removal."""

    CSS = """
    #info { padding: 1 2; color: $text-muted; }
    SelectionList { height: 1fr; margin: 0 2; }
    #confirm { dock: bottom; margin: 1 2; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, profiles: list[str]) -> None:
        super().__init__()
        self.profiles = profiles

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "\u2191/\u2193 to move, Space to toggle, Enter to confirm",
            id="info",
        )
        yield SelectionList(*[(p, p) for p in self.profiles])
        yield Button("Confirm", id="confirm")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(SelectionList).focus()

    def on_key(self, event: Key) -> None:
        focused = self.focused
        if isinstance(focused, Button) and event.key == "up":
            event.prevent_default()
            event.stop()
            self.query_one(SelectionList).focus()
        elif isinstance(focused, SelectionList) and event.key == "down":
            event.prevent_default()
            event.stop()
            self.query_one("#confirm", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        sel = self.query_one(SelectionList)
        self.exit(list(sel.selected))

    def action_cancel(self) -> None:
        self.exit([])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pick_session(
    sessions: list[str],
    host: str,
    capture: Callable[[str], str] | None = None,
) -> str | None:
    """Show a list of tmux session names; return chosen name or None.

    If *capture* is supplied, the picker shows a live preview of the
    highlighted session's active pane by calling ``capture(name)`` in a
    background worker.
    """
    app = SessionPicker(sessions, host, capture=capture)
    return app.run()


def pick_hosts(hosts: list[HostInfo]) -> list[HostInfo]:
    """Show the host picker TUI; return selected HostInfo objects."""
    result = HostPicker(hosts).run()
    return result or []


def pick_profiles(profiles: list[str]) -> list[str]:
    """Show a checklist of registered WT profiles; return checked names."""
    result = ProfilePicker(profiles).run()
    return result or []
