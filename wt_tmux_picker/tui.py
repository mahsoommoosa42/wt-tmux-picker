"""Interactive TUI pickers using Textual."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Button, Footer, Header, OptionList, SelectionList, Static
from textual.widgets.option_list import Option


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
            "↑/↓ to move, Enter to select, Escape for plain SSH",
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


class HostPicker(App[list[str]]):
    """Multi-select picker for SSH hosts during setup."""

    CSS = """
    #info { padding: 1 2; color: $text-muted; }
    SelectionList { height: 1fr; margin: 0 2; }
    #unavailable { padding: 1 2; color: $error; }
    #confirm { dock: bottom; margin: 1 2; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        eligible: list[str],
        unavailable: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__()
        self.eligible = eligible
        self.unavailable = unavailable or []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Select SSH hosts to set up\n"
            "Space to toggle, Enter to confirm, Escape to cancel",
            id="info",
        )
        if self.eligible:
            yield SelectionList(*[(h, h, True) for h in self.eligible])
        if self.unavailable:
            lines = "\n".join(
                f"  {host} — {reason}" for host, reason in self.unavailable
            )
            yield Static(f"Unavailable:\n{lines}", id="unavailable")
        yield Button("Confirm", id="confirm")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        nodes = self.query(SelectionList)
        if nodes:
            self.exit(list(nodes.first().selected))
        else:
            self.exit([])

    def action_cancel(self) -> None:
        self.exit([])


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


def pick_session(sessions: list[str], host: str) -> str | None:
    """Show a list of tmux session names; return chosen name or None."""
    app = SessionPicker(sessions, host)
    return app.run()


def pick_hosts(
    eligible: list[str],
    unavailable: list[tuple[str, str]] | None = None,
) -> list[str]:
    """Show a checklist of SSH hosts for setup; return checked names."""
    result = HostPicker(eligible, unavailable).run()
    return result or []


def pick_profiles(profiles: list[str]) -> list[str]:
    """Show a checklist of registered WT profiles; return checked names."""
    result = ProfilePicker(profiles).run()
    return result or []
