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
