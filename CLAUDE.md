# wt-tmux-picker Development Guide

## Project Overview

`wt-tmux-picker` is a Windows Terminal integration tool that automatically discovers SSH hosts from `~/.ssh/config`, checks if they have tmux and fzf installed, and registers Windows Terminal profiles that launch an interactive tmux session picker TUI.

**Key Features:**
- Automatic SSH host discovery from `~/.ssh/config`
- Interactive tmux session picker (prompt_toolkit-based TUI)
- Windows Terminal profile management (JSON settings.json manipulation)
- Fallback to plain SSH if no sessions found
- Cleanup with optional interactive profile removal picker
- 100% branch test coverage
- Dry-run mode for preview before applying changes

**Target Users:** Windows Terminal users who manage multiple remote machines and want fast tmux session access.

## Architecture

### Three Main Operations

```
setup  → Read SSH config → Check tmux/fzf → Add WT profiles
cleanup → List WT profiles → Interactive picker (or explicit hosts) → Remove profiles
attach → Pick session from list → Attach or fall back to SSH
```

### Module Structure

```
wt_tmux_picker/
├── __init__.py             # Public API
├── cli.py                  # Entry point, argument parsing, subcommands
├── tmux.py                 # Thin delegation to TmuxManager
├── ssh_config.py           # SSH config parsing
├── tui.py                  # TUI pickers (session, profiles)
├── windows_terminal.py     # WT settings.json read/write
tests/
├── unit/
│   ├── test_cli.py         # Subcommand tests, mocked TmuxManager
│   ├── test_tmux.py        # Delegation tests
│   ├── test_ssh_config.py  # SSH config parsing
│   ├── test_tui.py         # TUI picker tests
│   ├── test_windows_terminal.py  # Profile management tests
│   └── __init__.py
├── functional/
│   ├── test_setup.py       # End-to-end setup workflow
│   ├── test_cleanup.py     # End-to-end cleanup workflow
│   └── __init__.py
pyproject.toml
README.md
LICENSE
```

## Key Files and Their Roles

### `wt_tmux_picker/cli.py`
- **Entry Point:** `main()` → parses args → dispatches to subcommand
- **Subcommands:**
  - `_setup(user, ssh_config, dry_run, settings_path)` — register profiles
  - `_cleanup(dry_run, hosts, settings_path)` — remove profiles
  - `_attach(host, user)` — attach to session or fall back to SSH
- **Key Details:**
  - Uses `parse_ssh_hosts()` to read SSH config
  - Uses `TmuxManager` to check tool availability and list sessions
  - Uses `add_profile()` / `remove_tmux_profiles()` for WT settings
  - Uses TUI pickers for interactive workflows
- **Testing:** Mock `TmuxManager`, file I/O, TUI

### `wt_tmux_picker/tmux.py`
- **Purpose:** Thin delegation layer to `TmuxManager`
- **Functions:**
  - `has_tmux(host, user=None, *, dry_run=False)` → check tmux availability
  - `has_fzf(host, user=None, *, dry_run=False)` → check fzf availability
  - `list_sessions(host, user=None)` → get session names
- **Key Detail:** `dry_run=True` returns `True` (assumes tools present)
- **Testing:** Mock `TmuxManager`

### `wt_tmux_picker/ssh_config.py`
- **Function:** `parse_ssh_hosts(path: Path | None) → list[str]`
- **Purpose:** Extract host aliases from `~/.ssh/config`
- **Implementation:** Regex-based parser with `Include` directive support (follows globs, resolves relative paths against `~/.ssh/` per OpenSSH spec)
- **Testing:** Mock file I/O, test various SSH config formats

### `wt_tmux_picker/tui.py`
- **Purpose:** Interactive TUI pickers using prompt_toolkit
- **Functions:**
  - `pick_session(host, sessions)` → RadioList picker (single select)
  - `pick_profiles(profiles)` → CheckboxList picker (multi-select)
- **Return Values:**
  - `pick_session()` returns selected session name or `None` (Escape pressed)
  - `pick_profiles()` returns list of selected profile names
- **Testing:** Mock prompt_toolkit session creation and input

### `wt_tmux_picker/windows_terminal.py`
- **Purpose:** Read/write Windows Terminal settings.json
- **Key Functions:**
  - `load_settings(path) → dict` — parse JSON settings
  - `save_settings(settings, path)` — write JSON with pretty formatting
  - `add_profile(host, user, settings_path, dry_run) → bool` — register profile
  - `list_tmux_profiles(settings_path) → list[str]` — get " tmux" profiles
  - `remove_tmux_profiles(hosts, settings_path, dry_run) → list[str]` — remove profiles
- **Key Details:**
  - Profile name: `"{host} tmux"` (standard naming)
  - Profile GUID: `uuid5(uuid.NAMESPACE_DNS, host)` (deterministic)
  - Command: `"wt-tmux-picker attach --user {user} {host}"`
  - Settings path: `~/AppData/Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json`
- **Testing:** Mock `Path` operations, test JSON structure

## Testing Strategy

### Test Organization

**Unit Tests (mocked dependencies):**
- CLI argument parsing
- Subcommand logic (with mocked TmuxManager, file I/O)
- Profile management (with mocked file I/O)
- TUI behavior (with mocked input)

**Functional Tests (integration-level):**
- End-to-end setup workflow (reads SSH config, checks hosts, adds profiles)
- End-to-end cleanup workflow (lists profiles, removes selected)

### Coverage Requirements

**100% branch coverage required** (enforced by pytest `--cov-fail-under=100`)

To check:
```bash
pytest --cov=wt_tmux_picker --cov-report=term-missing
```

### Test Patterns

**Pattern 1: Mock TmuxManager**
```python
def test_setup_skips_hosts_without_tmux(self):
    with patch("wt_tmux_picker.cli.has_tmux", return_value=False):
        with patch("wt_tmux_picker.cli.add_profile") as mock_add:
            _setup(None, None, False)
    mock_add.assert_not_called()
```

**Pattern 2: Mock file I/O**
```python
def test_add_profile_updates_settings(self, tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"profiles": {"list": []}}')
    
    add_profile("devbox", None, settings_path=settings_file)
    
    data = json.loads(settings_file.read_text())
    assert any(p.get("name") == "devbox tmux" for p in data["profiles"]["list"])
```

**Pattern 3: Mock TUI picker**
```python
def test_attach_uses_user_selection(self):
    with patch("wt_tmux_picker.cli.TmuxManager.list_sessions", return_value=["s1", "s2"]):
        with patch("wt_tmux_picker.cli.pick_session", return_value="s1"):
            with patch("wt_tmux_picker.cli.TmuxManager.attach_session") as mock:
                _attach("devbox", None)
    mock.assert_called_once_with("s1")
```

## Common Development Tasks

### Running Tests
```bash
# All tests with coverage
pytest --cov=wt_tmux_picker --cov-report=term-missing

# Specific subcommand tests
pytest tests/unit/test_cli.py::TestSetup

# Functional test
pytest tests/functional/test_setup.py
```

### Adding a New Subcommand
1. Add parser configuration in `_build_parser()`
2. Add subcommand function `_mycommand(...)` in `cli.py`
3. Add dispatcher case in `main()`
4. Add unit tests in `test_cli.py`
5. Add functional test if integration-level
6. Verify `--cov-fail-under=100`

### Modifying Windows Terminal Profile Structure
1. Update `add_profile()` in `windows_terminal.py`
2. Update any constants like `_profile_name()`
3. Add/update tests in `test_windows_terminal.py`
4. Update README if profile format changed

### Debugging SSH Config Parsing
```bash
# Test SSH config parsing directly
python -c "from wt_tmux_picker.ssh_config import parse_ssh_hosts; print(parse_ssh_hosts())"

# Check Windows Terminal settings file
cat ~/AppData/Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json
```

## Windows Terminal Integration Details

### Profile Structure
```json
{
  "guid": "{<uuid5-based-guid>}",
  "name": "devbox tmux",
  "commandline": "wt-tmux-picker attach --user alice devbox",
  "hidden": false
}
```

### GUID Generation
- Uses `uuid.uuid5(uuid.NAMESPACE_DNS, hostname)`
- **Deterministic:** Same hostname always produces same GUID
- **Benefit:** Idempotent profile registration (safe to run setup multiple times)

### Settings File Location
```
~/AppData/Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json
```

**Important:** This is the default location. Users can override with custom settings path (for testing or alternate installations).

## Integration with TmuxManager

`tmux.py` provides a thin wrapper around `TmuxManager`:
```python
def has_tmux(host, user=None, *, dry_run=False):
    if dry_run:
        return True
    return TmuxManager(host, user).is_available()
```

This allows:
- **Mocking during tests:** Mock `TmuxManager` once in `cli.py`
- **Dry-run mode:** Return True without actual checks
- **Future enhancement:** Could cache results or add timeouts

## Dependencies and Constraints

**Runtime Dependencies:**
- `prompt_toolkit` — TUI pickers
- `tmux-manager` — SSH/tmux operations (from PyPI)

**Dev Dependencies:**
- `pytest`, `pytest-cov` — testing and coverage

**Python Version:** 3.12 only

**Platform:** Windows only (depends on Windows Terminal and Windows file paths)

## Design Decisions

### Why separate CLI arg parsing from subcommand logic?
- Allows testing CLI without running subcommand
- Allows mocking subcommands independently
- Clear separation of concerns

### Why thin delegation in tmux.py?
- Keeps TmuxManager dependency isolated
- Easy to swap implementation or add caching
- Simplifies testing (one mock point in cli.py)

### Why prompt_toolkit TUI instead of click?
- Native terminal UI without external deps
- Better UX than plain menu (keyboard navigation, visual feedback)
- Works on Windows Terminal

### Why UUID5 for profile GUIDs?
- Deterministic (same host → same GUID across runs)
- Safe for idempotent operations (run setup multiple times)
- Standard approach for stable UUIDs

## Windows Platform Restrictions

This tool targets Windows exclusively (Windows Terminal integration), but
the underlying `tmux-manager` library has platform-specific SSH behavior:

| Concern | Behavior on Windows |
|---|---|
| SSH ControlMaster | Not supported by Win32-OpenSSH — each SSH operation spawns a fresh process |
| Password auth | Prompts once **per SSH call** (setup checks each host, attach checks + attaches) |
| `connect()` on TmuxManager | Validates connectivity only — does not reduce password prompts |
| Recommended auth | SSH key-based (`IdentityFile` in `~/.ssh/config`) to avoid repeated prompts |

### Impact on subcommands

- **`setup`**: Checks `tmux` and `fzf` per host — 2 SSH calls per host, each may prompt for password with password auth
- **`attach`**: Calls `list_sessions()` then `attach_session()` — 2 SSH calls, each may prompt
- **`cleanup`**: Only reads local Windows Terminal settings.json — no SSH calls

### Mitigation

Configure SSH key-based auth for all managed hosts:

```
# ~/.ssh/config
Host devbox
    HostName 192.168.1.10
    User alice
    IdentityFile ~/.ssh/id_ed25519
```

This eliminates all password prompts across all subcommands.

## Known Limitations and Future Work

**Current Limitations:**
- Windows only (hardcoded Windows Terminal path)
- Password auth prompts once per SSH operation (see Windows Platform Restrictions above)
- No session filtering or sorting
- No customization of profile appearance

**Future Opportunities:**
- macOS/Linux terminal support (iTerm, tmux, alacritty)
- Configuration file for profile customization (colors, fonts)
- Session filtering (show only sessions matching pattern)
- Session history or favorites
- Multiple terminal applications (PowerShell, Conemu, etc.)

## Security Considerations

- **Settings file access:** Can read/write settings.json if user has permissions
- **SSH config parsing:** Regex-based parser for Host/Include directives
- **SSH key usage:** Relies on system SSH setup and permissions
- **No credential storage:** All auth via system SSH keys

## References

- [Windows Terminal Documentation](https://docs.microsoft.com/en-us/windows/terminal/)
- [Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/)
- [Tmux Manager Library](https://github.com/mahsoommoosa42/tmux-manager)
- [UUID5 for Stable IDs](https://docs.python.org/3/library/uuid.html#uuid.uuid5)
