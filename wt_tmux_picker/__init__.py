"""Windows Terminal + tmux session picker."""

from .ssh_config import parse_ssh_hosts
from .tmux import has_fzf, has_tmux, list_sessions
from .windows_terminal import add_profile, list_tmux_profiles, remove_tmux_profiles

__version__ = "0.1.0"

__all__ = [
    "parse_ssh_hosts",
    "has_tmux",
    "has_fzf",
    "list_sessions",
    "add_profile",
    "list_tmux_profiles",
    "remove_tmux_profiles",
]
