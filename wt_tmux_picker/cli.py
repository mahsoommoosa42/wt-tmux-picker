"""CLI entrypoint for wt-tmux-picker."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from tmux_manager import TmuxManager

from . import __version__
from .ssh_config import parse_ssh_hosts
from .tmux import has_fzf, has_tmux
from .tui import pick_profiles, pick_session
from .windows_terminal import (
    add_profile,
    list_tmux_profiles,
    remove_tmux_profiles,
    warn_jsonc_comments,
)


def _setup(
    user: str | None,
    ssh_config: Path | None,
    dry_run: bool,
    settings_path: Path | None = None,
) -> int:
    try:
        hosts = parse_ssh_hosts(ssh_config)
    except FileNotFoundError as exc:
        print(f"ERROR: SSH config not found: {exc}", file=sys.stderr)
        return 1

    if not hosts:
        print("No hosts found in SSH config.")
        return 0

    if not dry_run:
        warn_jsonc_comments(settings_path)

    for host in hosts:
        if not has_tmux(host, user, dry_run=dry_run):
            print(f"Checking {host} ...  tmux not found (skipped)")
            continue
        if not has_fzf(host, user, dry_run=dry_run):
            print(f"Checking {host} ...  fzf not found (skipped)")
            continue

        print(f"Checking {host} ...  tmux found, fzf found")

        if dry_run:
            print(f'[dry-run] Would add profile: "{host} tmux"')
            continue

        added = add_profile(host, user, settings_path=settings_path)
        if added:
            print(f'Added  Windows Terminal profile: "{host} tmux"')
        else:
            print(f'Skipped  "{host} tmux" (profile already exists)')

    return 0


def _cleanup(
    dry_run: bool,
    hosts: list[str] | None = None,
    settings_path: Path | None = None,
) -> int:
    if hosts:
        profile_names = [f"{h} tmux" for h in hosts]
    else:
        registered = list_tmux_profiles(settings_path=settings_path)
        if not registered:
            print("Nothing to clean up.")
            return 0
        profile_names = pick_profiles(registered)
        if not profile_names:
            print("Nothing removed.")
            return 0

    if not dry_run:
        warn_jsonc_comments(settings_path)

    removed = remove_tmux_profiles(
        profile_names, settings_path=settings_path, dry_run=dry_run
    )
    for name in removed:
        prefix = "[dry-run] Would remove" if dry_run else "Removed"
        print(f'{prefix}  Windows Terminal profile: "{name}"')

    if not removed:
        print("Nothing to clean up.")

    return 0


def _plain_ssh(host: str, user: str | None) -> None:
    """Open a plain SSH shell (no tmux) to *host*."""
    target = f"{user}@{host}" if user else host
    subprocess.run(["ssh", target])


def _attach(host: str, user: str | None) -> int:
    mgr = TmuxManager(host, user)
    sessions = mgr.list_sessions()

    if not sessions:
        _plain_ssh(host, user)
        return 0

    selected = pick_session(sessions, host)
    if selected:
        mgr.attach_session(selected)
    else:
        _plain_ssh(host, user)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wt-tmux-picker",
        description="Manage Windows Terminal tmux picker profiles.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    setup_p = sub.add_parser("setup", help="Install WT profiles for tmux hosts")
    setup_p.add_argument("--user", help="SSH username")
    setup_p.add_argument(
        "--ssh-config",
        type=Path,
        default=None,
        help="Path to SSH config (default: ~/.ssh/config)",
    )
    setup_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without making changes",
    )

    cleanup_p = sub.add_parser("cleanup", help="Remove WT tmux profiles")
    cleanup_p.add_argument(
        "hosts",
        nargs="*",
        help="Hosts to remove (omit for interactive TUI picker)",
    )
    cleanup_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without making changes",
    )

    attach_p = sub.add_parser("attach", help="Pick a tmux session and attach")
    attach_p.add_argument("host", help="SSH host to connect to")
    attach_p.add_argument("--user", help="SSH username")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "setup":
        return _setup(
            user=args.user,
            ssh_config=args.ssh_config,
            dry_run=args.dry_run,
        )
    elif args.command == "cleanup":
        return _cleanup(
            dry_run=args.dry_run,
            hosts=args.hosts or None,
        )
    else:
        return _attach(host=args.host, user=args.user)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
