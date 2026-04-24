"""Check remote host tool availability and list tmux sessions via SSH."""

from __future__ import annotations

import socket

import paramiko


def _ssh_exec(host: str, user: str | None, command: str) -> tuple[int, str]:
    """Execute *command* on *host* via paramiko; return (exit_status, stdout).

    Returns (-1, "") on any connection, auth, or network failure.
    """
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            username=user,
            timeout=5,
            look_for_keys=True,
            allow_agent=True,
        )
        _, stdout, _ = client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        return exit_status, output
    except (paramiko.SSHException, socket.timeout, OSError):
        return -1, ""
    finally:
        client.close()


def _has_command(
    host: str,
    user: str | None,
    command: str,
    *,
    dry_run: bool = False,
) -> bool:
    """Return True if *command* is on PATH on *host* via SSH."""
    if dry_run:
        return True
    exit_status, _ = _ssh_exec(host, user, f"command -v {command}")
    return exit_status == 0


def has_tmux(
    host: str,
    user: str | None = None,
    *,
    dry_run: bool = False,
) -> bool:
    """Return True if tmux is found on *host* via SSH."""
    return _has_command(host, user, "tmux", dry_run=dry_run)


def has_fzf(
    host: str,
    user: str | None = None,
    *,
    dry_run: bool = False,
) -> bool:
    """Return True if fzf is found on *host* via SSH."""
    return _has_command(host, user, "fzf", dry_run=dry_run)


def list_sessions(host: str, user: str | None = None) -> list[str]:
    """Return tmux session names on *host*, or [] if none/unreachable."""
    exit_status, output = _ssh_exec(
        host, user, "tmux list-sessions -F '#{session_name}' 2>/dev/null"
    )
    if exit_status != 0 or not output.strip():
        return []
    return [s for s in output.strip().splitlines() if s]
