# chromium-profile-cli

Command-line tool for accessing Chromium browser data (tabs, history, bookmarks).

Works with **Brave**, **Chrome**, and **Chromium**.

## Installation

```bash
# Using uvx (recommended)
uvx chromium-profile-cli

# Or install with pip
pip install chromium-profile-cli
```

## First Run

On first run, chromium-profile-cli will automatically detect installed browsers and prompt you to select one:

```bash
$ chromium-profile-cli status

🔍 Multiple browser profiles detected:

  1. brave      /Users/you/Library/Application Support/BraveSoftware/Brave-Browser/Default
  2. chrome     /Users/you/Library/Application Support/Google/Chrome/Default

Select a browser [1]: 1

💾 Save as default? [Y/n]: y
✓ Saved to ~/.config/chromium-sync/profile
```

## Commands

### Configuration

```bash
# Show current configuration
chromium-profile-cli config show

# Interactively select a browser
chromium-profile-cli config set

# Manually set profile path
chromium-profile-cli config set-path /path/to/profile
```

### Tabs

```bash
# Show local browser tabs
chromium-profile-cli tabs local

# Show tabs from all synced devices
chromium-profile-cli tabs synced

# JSON output
chromium-profile-cli tabs local --json
```

### History

```bash
# Search by text (substring match)
chromium-profile-cli history -q github

# Search by regex pattern
chromium-profile-cli history -p "docs\\.python\\.org"

# Limit results
chromium-profile-cli history -q python -l 50

# Filter by date
chromium-profile-cli history --days 7
chromium-profile-cli history --after 2026-01-01
chromium-profile-cli history --before 2026-02-01

# JSON output
chromium-profile-cli history -q python --json
```

### Bookmarks

```bash
# List all bookmarks
chromium-profile-cli bookmarks list

# Search bookmarks
chromium-profile-cli bookmarks search python

# Filter by folder ID
chromium-profile-cli bookmarks list --folder 123

# JSON output
chromium-profile-cli bookmarks search python --json
```

### Status

```bash
# Check what data is accessible
chromium-profile-cli status
```

## Environment Variables

Set `CHROMIUM_PROFILE_PATH` to override auto-detection:

```bash
export CHROMIUM_PROFILE_PATH=~/.config/google-chrome/Default
chromium-profile-cli status
```

## How It Works

Reads directly from your browser's local profile files:

- **History**: SQLite database
- **Bookmarks**: JSON file
- **Synced Tabs**: LevelDB (contains tabs from all your synced devices)

No authentication or network requests required.

## License

Apache 2.0
