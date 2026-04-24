"""Interactive TUI pickers using prompt_toolkit."""

from __future__ import annotations

from prompt_toolkit.shortcuts import checkboxlist_dialog, radiolist_dialog


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
