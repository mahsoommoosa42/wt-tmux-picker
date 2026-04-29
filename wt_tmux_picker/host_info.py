"""SSH host metadata gathering via batched probing."""

from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass, field

_VIEW_COUNT = 3


@dataclass
class HostInfo:
    """Metadata gathered about an SSH host."""

    name: str
    user: str | None = None
    platform: str = "Unknown"
    ip: str = "N/A"
    auth: str = "unknown"
    has_tmux: bool = False
    has_fzf: bool = False
    manual: bool = False

    @property
    def eligible(self) -> bool:
        """True when both tmux and fzf are present."""
        return self.has_tmux and self.has_fzf

    @property
    def missing_tools(self) -> list[str]:
        """Names of required tools that are absent."""
        tools: list[str] = []
        if not self.has_tmux:
            tools.append("tmux")
        if not self.has_fzf:
            tools.append("fzf")
        return tools

    def label(self, view: int = 0) -> str:
        """Format display label for the given view level.

        View 0: Name + Platform
        View 1: Name + Platform + IP
        View 2: Name + Platform + IP + Auth
        """
        parts = [self.name, f"[{self.platform}]"]
        if view >= 1:
            parts.append(f"({self.ip})")
        if view >= 2:
            parts.append(f"auth: {self.auth}")
        return "  ".join(parts)

    def unavailable_label(self, view: int = 0) -> str:
        """Format label with missing-tool annotation."""
        missing = ", ".join(self.missing_tools)
        return f"{self.label(view)} \u2014 {missing} not found"


# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------

def _ssh_target(host: str, user: str | None) -> str:
    return f"{user}@{host}" if user else host


def _resolve_hostname(host: str) -> str:
    """Return the real hostname SSH would connect to (parses ``ssh -G``)."""
    try:
        result = subprocess.run(
            ["ssh", "-G", host],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("hostname "):
                    return line.split(None, 1)[1]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return host


def _resolve_ip(hostname: str) -> str:
    """DNS-resolve *hostname* to an IP address."""
    try:
        results = socket.getaddrinfo(hostname, None)
        if results:
            return results[0][4][0]
    except (socket.gaierror, OSError):
        pass
    return "N/A"


def _map_platform(uname_output: str) -> str:
    name = uname_output.strip().lower()
    if "linux" in name:
        return "Linux"
    if "darwin" in name:
        return "macOS"
    if any(w in name for w in ("mingw", "msys", "cygwin", "windows")):
        return "Windows"
    return uname_output.strip() or "Unknown"


def _probe_ssh(
    host: str,
    user: str | None,
    *,
    batch_mode: bool = False,
) -> tuple[int, str]:
    """Run a single SSH command that returns platform, tmux, and fzf status.

    Returns ``(exit_code, stdout)``.
    """
    target = _ssh_target(host, user)
    cmd = (
        'printf "%s\\n" '
        '"$(uname -s)" '
        '"$(command -v tmux >/dev/null 2>&1 && echo yes || echo no)" '
        '"$(command -v fzf >/dev/null 2>&1 && echo yes || echo no)"'
    )
    args = ["ssh", "-o", "ConnectTimeout=5"]
    if batch_mode:
        args += ["-o", "BatchMode=yes"]
    args += [target, cmd]
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=15,
        )
        return result.returncode, result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""


def _parse_probe(output: str) -> tuple[str, bool, bool]:
    """Parse the three-line output from ``_probe_ssh``."""
    lines = output.strip().splitlines()
    platform = _map_platform(lines[0]) if lines else "Unknown"
    has_tmux = lines[1].strip() == "yes" if len(lines) > 1 else False
    has_fzf = lines[2].strip() == "yes" if len(lines) > 2 else False
    return platform, has_tmux, has_fzf


def probe_host(
    host: str,
    user: str | None = None,
    *,
    dry_run: bool = False,
) -> HostInfo:
    """Gather metadata about *host* using at most two SSH calls.

    1. Try key-based auth (``BatchMode=yes``) — if it works, one SSH
       call provides platform, tmux, fzf, and auth type.
    2. If key auth fails, fall back to regular SSH (may prompt for
       password) for the same data, and record auth as ``"password"``.

    IP resolution is a local DNS lookup (no SSH).
    """
    if dry_run:
        return HostInfo(name=host, user=user, has_tmux=True, has_fzf=True)

    real_hostname = _resolve_hostname(host)
    ip = _resolve_ip(real_hostname)

    # Try key-based auth first (no password prompt).
    code, output = _probe_ssh(host, user, batch_mode=True)
    if code == 0:
        platform, has_tmux, has_fzf = _parse_probe(output)
        return HostInfo(
            name=host, user=user, platform=platform, ip=ip,
            auth="key", has_tmux=has_tmux, has_fzf=has_fzf,
        )

    # Fall back to interactive SSH (may prompt for password).
    code, output = _probe_ssh(host, user, batch_mode=False)
    if code == 0:
        platform, has_tmux, has_fzf = _parse_probe(output)
        return HostInfo(
            name=host, user=user, platform=platform, ip=ip,
            auth="password", has_tmux=has_tmux, has_fzf=has_fzf,
        )

    # Host unreachable.
    return HostInfo(name=host, user=user, ip=ip)
