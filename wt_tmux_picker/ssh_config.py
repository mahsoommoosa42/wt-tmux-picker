"""Parse ~/.ssh/config and extract host entries."""

from __future__ import annotations

import re
from pathlib import Path


def parse_ssh_hosts(config_path: Path | None = None) -> list[str]:
    """Return all non-wildcard Host entries from an SSH config file.

    Raises FileNotFoundError if the config file does not exist.
    """
    if config_path is None:
        config_path = Path.home() / ".ssh" / "config"

    text = config_path.read_text(encoding="utf-8")
    hosts: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        m = re.match(r"^host\s+(.+)$", stripped, re.IGNORECASE)
        if not m:
            continue
        for token in m.group(1).split():
            if "*" not in token and "?" not in token:
                hosts.append(token)
    return hosts
