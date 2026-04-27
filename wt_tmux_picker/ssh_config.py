"""Parse ~/.ssh/config and extract host entries."""

from __future__ import annotations

import glob
import re
from pathlib import Path


def _parse_file(config_path: Path, seen: set[Path]) -> list[str]:
    """Extract hosts from a single SSH config file, following Include."""
    resolved = config_path.resolve()
    if resolved in seen:
        return []
    seen.add(resolved)

    text = config_path.read_text(encoding="utf-8")
    hosts: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()

        m_include = re.match(r"^include\s+(.+)$", stripped, re.IGNORECASE)
        if m_include:
            pattern = m_include.group(1).strip()
            if pattern.startswith("~"):
                pattern = str(Path.home()) + pattern[1:]
            elif not Path(pattern).is_absolute():
                # OpenSSH resolves relative Include paths against ~/.ssh/
                pattern = str(Path.home() / ".ssh" / pattern)
            for match in sorted(glob.glob(pattern)):
                p = Path(match)
                if p.is_file():
                    hosts.extend(_parse_file(p, seen))
            continue

        m = re.match(r"^host\s+(.+)$", stripped, re.IGNORECASE)
        if not m:
            continue
        for token in m.group(1).split():
            if "*" not in token and "?" not in token:
                hosts.append(token)
    return hosts


def parse_ssh_hosts(config_path: Path | None = None) -> list[str]:
    """Return all non-wildcard Host entries from an SSH config file.

    Follows Include directives to discover hosts in referenced files.

    Raises FileNotFoundError if the config file does not exist.
    """
    if config_path is None:
        config_path = Path.home() / ".ssh" / "config"

    return _parse_file(config_path, set())
