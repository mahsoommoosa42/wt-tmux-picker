"""Thin wrappers delegating to tmux-manager for remote host checks."""

from __future__ import annotations

from tmux_manager import TmuxManager


def has_tmux(host: str, user: str | None = None, *, dry_run: bool = False) -> bool:
    """Return True if tmux is found on *host*."""
    if dry_run:
        return True
    return TmuxManager(host, user).is_available()


def has_fzf(host: str, user: str | None = None, *, dry_run: bool = False) -> bool:
    """Return True if fzf is found on *host*."""
    if dry_run:
        return True
    return TmuxManager(host, user).command_available("fzf")


def list_sessions(host: str, user: str | None = None) -> list[str]:
    """Return tmux session names on *host*, or [] if none/unreachable."""
    return TmuxManager(host, user).list_sessions()


def session_info(host: str, user: str | None = None, *, name: str) -> dict | None:
    """Return metadata dict for session *name* on *host*, or None."""
    return TmuxManager(host, user).session_info(name)


def capture_pane(
    host: str, user: str | None = None, *, name: str, lines: int = 50
) -> str:
    """Capture visible pane content from session *name* on *host*."""
    return TmuxManager(host, user).capture_pane(name, lines)
