"""Interactive TUI pickers using Textual."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, OptionList, SelectionList, Static
from textual.widgets.option_list import Option

from .host_info import HostInfo, _VIEW_COUNT


class SessionPicker(App[str | None]):
    """Single-select picker for tmux session names."""

    CSS = """
    #info { padding: 1 2; color: $text-muted; }
    OptionList { height: 1fr; margin: 0 2; }
    """
    BINDINGS = [("escape", "cancel", "Plain SSH")]

    def __init__(self, sessions: list[str], host: str) -> None:
        super().__init__()
        self.sessions = sessions
        self.host = host

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            f"tmux sessions on {self.host}\n"
            "\u2191/\u2193 to move, Enter to select, Escape for plain SSH",
            id="info",
        )
        yield OptionList(*[Option(s, id=s) for s in self.sessions])
        yield Footer()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.exit(str(event.option.id))

    def action_cancel(self) -> None:
        self.exit(None)


# ---------------------------------------------------------------------------
# Manual host entry dialog
# ---------------------------------------------------------------------------

class ManualHostScreen(ModalScreen[tuple[str, str | None] | None]):
    """Modal dialog for entering a hostname and optional username."""

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

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Hostname:")
            yield Input(placeholder="e.g. devbox.example.com", id="hostname")
            yield Static("Username (optional):")
            yield Input(placeholder="e.g. alice", id="username")
            with Horizontal(id="btn-bar"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Cancel", id="cancel-dialog")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            hostname = self.query_one("#hostname", Input).value.strip()
            if not hostname:
                return
            raw_user = self.query_one("#username", Input).value.strip()
            self.dismiss((hostname, raw_user or None))
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
            "Space to toggle, [v] cycle view, Escape to cancel",
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

    def _on_manual_host(self, result: tuple[str, str | None] | None) -> None:
        if result is None:
            return
        hostname, username = result
        info = HostInfo(
            name=hostname, user=username, manual=True,
            has_tmux=True, has_fzf=True,
        )
        self._manual.append(info)
        self._refresh_selection_list()

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
        sl.clear_options()
        for info in self._eligible + self._manual:
            label = info.label(self._view)
            checked = info.name in selected if not first_load else True
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
        yield Static("Space to toggle, Enter to confirm", id="info")
        yield SelectionList(*[(p, p) for p in self.profiles])
        yield Button("Confirm", id="confirm")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        sel = self.query_one(SelectionList)
        self.exit(list(sel.selected))

    def action_cancel(self) -> None:
        self.exit([])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pick_session(sessions: list[str], host: str) -> str | None:
    """Show a list of tmux session names; return chosen name or None."""
    app = SessionPicker(sessions, host)
    return app.run()


def pick_hosts(hosts: list[HostInfo]) -> list[HostInfo]:
    """Show the host picker TUI; return selected HostInfo objects."""
    result = HostPicker(hosts).run()
    return result or []


def pick_profiles(profiles: list[str]) -> list[str]:
    """Show a checklist of registered WT profiles; return checked names."""
    result = ProfilePicker(profiles).run()
    return result or []
