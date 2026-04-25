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

## Development

### Local Setup

Clone the repo and install in editable mode:

```bash
git clone https://github.com/mahsoommoosa42/wt-tmux-picker.git
cd wt-tmux-picker
uv sync --extra dev
```

#### Using Local tmux-manager for Development

If you're also developing [tmux-manager](https://github.com/mahsoommoosa42/tmux-manager), you can use your local version instead of the PyPI release:

```bash
# Clone tmux-manager in a sibling directory
cd ..
git clone https://github.com/mahsoommoosa42/tmux-manager.git
cd wt-tmux-picker

# Add to pyproject.toml [tool.uv.sources]:
# [tool.uv.sources]
# tmux-manager = {path = "../tmux-manager", editable = true}

# Then sync dependencies:
uv sync --extra dev
```

This will install tmux-manager from your local clone instead of PyPI.

### Run Tests

```bash
uv run pytest --cov=wt_tmux_picker --cov-report=term-missing
```

All tests must pass at 100% branch coverage before submitting a PR.

### Project Structure

See [CLAUDE.md](CLAUDE.md) for detailed architecture, module documentation, testing patterns, and design decisions.

## Contributing

### Opening a Pull Request

1. **Fork and clone:** Fork the repo, then clone your fork locally
2. **Create a branch:** `git checkout -b fix/issue-name` or `feat/feature-name`
3. **Set up development:** Follow the "Local Setup" section above
4. **Make changes:** Write code, add tests, update docs as needed
5. **Run tests:** Ensure `uv run pytest --cov-fail-under=100` passes
6. **Commit:** Write clear, concise commit messages
7. **Push:** `git push origin your-branch`
8. **Open PR:** Open a pull request on GitHub with a description of your changes

### Guidelines

- All new code must have 100% branch test coverage
- Follow existing code style (see CLAUDE.md for patterns)
- Update README.md if adding new features or subcommands
- Use `TmuxManager` from tmux-manager for all tmux operations (don't add new SSH logic to this repo)

## License

GNU General Public License v3. See [LICENSE](LICENSE).
