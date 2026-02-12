# Chromium CLI - Project Status

## What's Been Built

A command-line tool for interacting with Chromium browser data (tabs, history, bookmarks). This is a separate project from the chromium-sync-mcp MCP server.

### Project Structure

```
chromium-cli/
├── src/
│   └── chromium_cli/
│       ├── __init__.py
│       └── main.py          # CLI implementation
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── setup-dev.sh              # Development setup script
└── STATUS.md                 # This file
```

### Features Implemented

The CLI provides the following commands:

- `chromium-cli config` - Manage browser profile configuration
  - `config show` - Show current configuration
  - `config set` - Interactively select browser
  - `config set-path <path>` - Set profile path directly

- `chromium-cli tabs` - View browser tabs
  - `tabs local` - Local browser session tabs
  - `tabs synced` - Tabs from all synced devices

- `chromium-cli history` - Search browsing history
  - Supports text search, regex patterns, date filtering
  - JSON output option

- `chromium-cli bookmarks` - View and search bookmarks
  - `bookmarks list` - List all bookmarks
  - `bookmarks search <query>` - Search by title/URL

- `chromium-cli status` - Check what data is accessible

### First-Run Experience

On first run, the tool automatically:
1. Detects all installed Chromium-based browsers
2. Prompts user to select one
3. Offers to save the selection as default

## Current Issue

### plyvel Runtime Linking Problem

The project has a runtime linking issue with plyvel on macOS:

```
ImportError: dlopen(.../_plyvel.cpython-313-darwin.so, 0x0002):
  symbol not found in flat namespace '__ZTIN7leveldb10ComparatorE'
```

**Root Cause**: The leveldb library installed via Homebrew was compiled without RTTI (Run-Time Type Information), but plyvel expects these symbols.

**What Works**:
- ✅ Build-time compilation (plyvel builds successfully)
- ✅ Linking (correct library path)

**What Doesn't Work**:
- ❌ Runtime loading (missing typeinfo symbols)

### Possible Solutions

1. **Rebuild leveldb with RTTI** (complex, requires custom Homebrew formula)
2. **Use a different LevelDB wrapper** (would require changes to chromium-sync-mcp)
3. **Find pre-built wheels** (none available for Python 3.13 + macOS ARM64)
4. **Test if chromium-sync-mcp itself works** (need to verify if this affects the MCP server too)

## Next Steps

1. Determine if the chromium-sync-mcp server has the same issue or if it works
2. If it works, understand why (different environment? Different install method?)
3. Either fix the issue or document the limitation clearly
4. Set up GitHub repository
5. Publish to PyPI (once runtime issue is resolved)

## Files Created

### In chromium-sync-mcp (reverted)
- ~~src/chromium_sync/cli.py~~ (removed - moved to separate project)
- pyproject.toml (reverted - removed click dependency and cli entry point)

### In chromium-cli/main
- All files in `/Users/jaidhyani/projects/chromium-cli/main/`
- Git repository initialized but not yet committed
