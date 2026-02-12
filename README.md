# chromium-cli

Command-line tool for accessing Chromium browser data (tabs, history, bookmarks).

Works with **Brave**, **Chrome**, and **Chromium**.

## Installation

```bash
# Using uvx (recommended)
uvx chromium-cli

# Or install with pip
pip install chromium-cli
```

### System Requirements

Requires the LevelDB library (inherited from chromium-sync-mcp):

```bash
# macOS
brew install leveldb

# Ubuntu/Debian
sudo apt-get install libleveldb-dev

# Fedora
sudo dnf install leveldb-devel
```

## First Run

On first run, chromium-cli will automatically detect installed browsers and prompt you to select one:

```bash
$ chromium-cli status

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
chromium-cli config show

# Interactively select a browser
chromium-cli config set

# Manually set profile path
chromium-cli config set-path /path/to/profile
```

### Tabs

```bash
# Show local browser tabs
chromium-cli tabs local

# Show tabs from all synced devices
chromium-cli tabs synced

# JSON output
chromium-cli tabs local --json
```

### History

```bash
# Search by text (substring match)
chromium-cli history -q github

# Search by regex pattern
chromium-cli history -p "docs\\.python\\.org"

# Limit results
chromium-cli history -q python -l 50

# Filter by date
chromium-cli history --days 7
chromium-cli history --after 2026-01-01
chromium-cli history --before 2026-02-01

# JSON output
chromium-cli history -q python --json
```

### Bookmarks

```bash
# List all bookmarks
chromium-cli bookmarks list

# Search bookmarks
chromium-cli bookmarks search python

# Filter by folder ID
chromium-cli bookmarks list --folder 123

# JSON output
chromium-cli bookmarks search python --json
```

### Status

```bash
# Check what data is accessible
chromium-cli status
```

## Environment Variables

Set `CHROMIUM_PROFILE_PATH` to override auto-detection:

```bash
export CHROMIUM_PROFILE_PATH=~/.config/google-chrome/Default
chromium-cli status
```

## How It Works

This tool uses the [chromium-sync-mcp](https://github.com/jaidhyani/chromium-sync-mcp) library to read directly from your browser's local profile files:

- **History**: SQLite database
- **Bookmarks**: JSON file
- **Synced Tabs**: LevelDB (contains tabs from all your synced devices)

No authentication or network requests required.

## License

Apache 2.0
