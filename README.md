# wt-tmux-picker

Automatically register Windows Terminal profiles that open an interactive tmux session picker for your SSH hosts.

When you open a registered profile, a TUI dropdown lists your live tmux sessions. Select one to attach, or press Escape to open a plain SSH shell.

```
  Select tmux session on devbox:

  ┌────────────────────┐
  │ > main             │
  │   work             │
  │   logs             │
  └────────────────────┘

  ↑/↓ to move, Enter to select, Escape for plain SSH
```

## Prerequisites

- Windows Terminal
- Python 3.10+
- SSH key authentication (no password prompts) configured for each host
- `tmux` installed on remote hosts
- `fzf` installed on remote hosts

## Install

```
uv add wt-tmux-picker
```

or with pip:

```
pip install wt-tmux-picker
```

## Usage

### Setup

Reads `~/.ssh/config`, connects to each host via SSH to check for `tmux` and `fzf`, then registers a Windows Terminal profile for each qualifying host.

```
wt-tmux-picker setup
```

Options:

| Flag | Description |
|---|---|
| `--user NAME` | SSH username to use for all hosts |
| `--ssh-config PATH` | Path to SSH config (default: `~/.ssh/config`) |
| `--dry-run` | Preview actions without making changes |

### Cleanup

Remove registered profiles. With no arguments, an interactive TUI lets you choose which profiles to remove.

```
wt-tmux-picker cleanup               # TUI picker
wt-tmux-picker cleanup devbox        # remove one host
wt-tmux-picker cleanup devbox prod   # remove specific hosts
```

Options:

| Flag | Description |
|---|---|
| `--dry-run` | Preview removals without making changes |

### Attach (used by profiles internally)

Invoked automatically by Windows Terminal profiles. You can also call it directly.

```
wt-tmux-picker attach devbox
wt-tmux-picker attach devbox --user alice
```

## License

GNU General Public License v3. See [LICENSE](LICENSE).
