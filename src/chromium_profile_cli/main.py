"""Command-line interface for Chromium browser data access.

Provides direct CLI access to browser tabs, history, and bookmarks.
"""

import json
import sys
from pathlib import Path

import click
from chromium_profile_cli.local import (
    CONFIG_FILE,
    LocalReader,
    MultipleProfilesFound,
    find_all_browser_profiles,
    load_saved_profile,
    resolve_browser_profile,
    save_profile_choice,
)


def get_reader() -> LocalReader:
    """Get or initialize a LocalReader instance.

    On first run, prompts user to select a browser profile.
    """
    try:
        profile_path = resolve_browser_profile()
        return LocalReader(profile_path)
    except MultipleProfilesFound as e:
        click.echo("\n🔍 Multiple browser profiles detected:\n")
        browsers = list(e.profiles.keys())
        for i, (name, path) in enumerate(e.profiles.items(), 1):
            click.echo(f"  {i}. {name:<10} {path}")

        click.echo()
        choice = click.prompt(
            "Select a browser",
            type=click.IntRange(1, len(browsers)),
            default=1,
        )

        selected_name = browsers[choice - 1]
        selected_path = e.profiles[selected_name]

        if click.confirm("\n💾 Save as default?", default=True):
            save_profile_choice(selected_path)
            click.echo(f"✓ Saved to {CONFIG_FILE}")

        return LocalReader(selected_path)
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("\nSet CHROMIUM_PROFILE_PATH to your browser profile directory,", err=True)
        click.echo("or run 'chromium-profile-cli config set'", err=True)
        sys.exit(1)


@click.group()
@click.version_option(version="0.2.0")
def cli():
    """CLI tool for accessing Chromium browser data.

    Access tabs, history, and bookmarks from Brave, Chrome, or Chromium.
    """
    pass


@cli.group()
def config():
    """Manage browser profile configuration."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    saved = load_saved_profile()
    if saved:
        click.echo(f"Profile: {saved}")
    else:
        click.echo("No saved profile configuration.")
        click.echo("\nAvailable browsers:")
        profiles = find_all_browser_profiles()
        if profiles:
            for name, path in profiles.items():
                click.echo(f"  - {name}: {path}")
        else:
            click.echo("  (none found)")


@config.command("set")
def config_set():
    """Interactively select and save a browser profile."""
    profiles = find_all_browser_profiles()

    if not profiles:
        click.echo("❌ No browser profiles found.", err=True)
        sys.exit(1)

    click.echo("\n🔍 Available browser profiles:\n")
    browsers = list(profiles.keys())
    for i, (name, path) in enumerate(profiles.items(), 1):
        click.echo(f"  {i}. {name:<10} {path}")

    click.echo()
    choice = click.prompt(
        "Select a browser",
        type=click.IntRange(1, len(browsers)),
        default=1,
    )

    selected_name = browsers[choice - 1]
    selected_path = profiles[selected_name]

    save_profile_choice(selected_path)
    click.echo(f"\n✓ Saved {selected_name} profile to {CONFIG_FILE}")


@config.command("set-path")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def config_set_path(path: Path):
    """Set browser profile path directly."""
    save_profile_choice(path)
    click.echo(f"✓ Saved profile path to {CONFIG_FILE}")


@cli.group()
def tabs():
    """View open browser tabs."""
    pass


@tabs.command("local")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tabs_local(as_json: bool):
    """Show tabs from local browser session."""
    reader = get_reader()
    try:
        tab_list = reader.get_local_tabs()

        if as_json:
            data = [{"url": t.url, "title": t.title} for t in tab_list]
            click.echo(json.dumps(data, indent=2))
        else:
            if not tab_list:
                click.echo("No open tabs found.")
            else:
                click.echo(f"\n📑 Found {len(tab_list)} open tabs:\n")
                for tab in tab_list:
                    if tab.title:
                        click.echo(f"  • {tab.title}")
                        click.echo(f"    {click.style(tab.url, dim=True)}")
                    else:
                        click.echo(f"  • {tab.url}")
    finally:
        reader.close()


@tabs.command("synced")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tabs_synced(as_json: bool):
    """Show tabs from all synced devices."""
    reader = get_reader()
    try:
        devices = reader.get_tabs()

        if as_json:
            data = [
                {
                    "device": d.name,
                    "type": d.device_type,
                    "tabs": [{"url": t.url, "title": t.title} for t in d.tabs],
                }
                for d in devices
            ]
            click.echo(json.dumps(data, indent=2))
        else:
            if not devices:
                click.echo("No synced devices found.")
            else:
                for device in devices:
                    click.echo(f"\n📱 {device.name} ({device.device_type})")
                    if device.tabs:
                        for tab in device.tabs:
                            if tab.title:
                                click.echo(f"  • {tab.title}")
                                click.echo(f"    {click.style(tab.url, dim=True)}")
                            else:
                                click.echo(f"  • {tab.url}")
                    else:
                        click.echo("  (no tabs)")
    finally:
        reader.close()


@cli.command()
@click.option("-q", "--query", help="Search text (substring match)")
@click.option("-p", "--pattern", help="Regex pattern to match")
@click.option("-l", "--limit", default=100, help="Maximum results (default: 100)")
@click.option("--days", "days_back", type=int, help="Only last N days")
@click.option("--after", help="Only after this date (YYYY-MM-DD)")
@click.option("--before", help="Only before this date (YYYY-MM-DD)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def history(
    query: str | None,
    pattern: str | None,
    limit: int,
    days_back: int | None,
    after: str | None,
    before: str | None,
    as_json: bool,
):
    """Search browsing history.

    Examples:

      chromium-profile-cli history -q github

      chromium-profile-cli history -p "docs\\.python\\.org"

      chromium-profile-cli history --days 7 -l 50

      chromium-profile-cli history --after 2026-01-01
    """
    reader = get_reader()
    try:
        entries = reader.get_history(
            query=query,
            pattern=pattern,
            limit=limit,
            days_back=days_back,
            after=after,
            before=before,
        )

        if as_json:
            data = [
                {
                    "url": e.url,
                    "title": e.title,
                    "visit_time": e.visit_time.isoformat(),
                    "visit_count": e.visit_count,
                }
                for e in entries
            ]
            click.echo(json.dumps(data, indent=2))
        else:
            if not entries:
                click.echo("No history entries found.")
            else:
                click.echo(f"\n📜 Found {len(entries)} history entries:\n")
                for entry in entries:
                    visit_time = entry.visit_time.strftime("%Y-%m-%d %H:%M")
                    count_str = f"({entry.visit_count}×)" if entry.visit_count > 1 else ""
                    click.echo(f"  • {entry.title}")
                    click.echo(f"    {click.style(entry.url, dim=True)}")
                    click.echo(f"    {click.style(f'{visit_time} {count_str}', dim=True)}")
                    click.echo()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        reader.close()


@cli.group()
def bookmarks():
    """View and search bookmarks."""
    pass


@bookmarks.command("list")
@click.option("--folder", help="Filter by folder ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def bookmarks_list(folder: str | None, as_json: bool):
    """List all bookmarks."""
    reader = get_reader()
    try:
        bookmark_list = reader.get_bookmarks(folder_id=folder)

        if as_json:
            data = [
                {
                    "id": b.id,
                    "title": b.title,
                    "url": b.url,
                    "is_folder": b.is_folder,
                    "parent_id": b.parent_id,
                }
                for b in bookmark_list
            ]
            click.echo(json.dumps(data, indent=2))
        else:
            if not bookmark_list:
                click.echo("No bookmarks found.")
            else:
                click.echo(f"\n🔖 Found {len(bookmark_list)} bookmarks:\n")
                for bm in bookmark_list:
                    if bm.is_folder:
                        click.echo(f"  📁 {bm.title} (id: {bm.id})")
                    else:
                        click.echo(f"  • {bm.title}")
                        click.echo(f"    {click.style(bm.url, dim=True)}")
    finally:
        reader.close()


@bookmarks.command("search")
@click.argument("query")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def bookmarks_search(query: str, as_json: bool):
    """Search bookmarks by title or URL."""
    reader = get_reader()
    try:
        results = reader.search_bookmarks(query)

        if as_json:
            data = [
                {
                    "id": b.id,
                    "title": b.title,
                    "url": b.url,
                    "is_folder": b.is_folder,
                }
                for b in results
            ]
            click.echo(json.dumps(data, indent=2))
        else:
            if not results:
                click.echo(f"No bookmarks matching '{query}'.")
            else:
                click.echo(f"\n🔖 Found {len(results)} matching bookmarks:\n")
                for bm in results:
                    if bm.is_folder:
                        click.echo(f"  📁 {bm.title}")
                    else:
                        click.echo(f"  • {bm.title}")
                        click.echo(f"    {click.style(bm.url, dim=True)}")
    finally:
        reader.close()


@cli.command()
def status():
    """Check what browser data is accessible."""
    reader = get_reader()
    try:
        click.echo(f"\n📊 Browser Data Status\n")
        click.echo(f"Profile: {reader.profile_path}\n")

        status_items = []

        try:
            hist = reader.get_history(limit=1)
            status_items.append(("History", "✓", f"{len(hist)} entries sampled"))
        except Exception as e:
            status_items.append(("History", "✗", str(e)))

        try:
            bm = reader.get_bookmarks()
            status_items.append(("Bookmarks", "✓", f"{len(bm)} items"))
        except Exception as e:
            status_items.append(("Bookmarks", "✗", str(e)))

        try:
            local = reader.get_local_tabs()
            status_items.append(("Local tabs", "✓", f"{len(local)} tabs"))
        except Exception as e:
            status_items.append(("Local tabs", "✗", str(e)))

        try:
            devices = reader.get_tabs()
            total_tabs = sum(len(d.tabs) for d in devices)
            if devices:
                status_items.append(
                    ("Synced tabs", "✓", f"{len(devices)} devices, {total_tabs} tabs")
                )
            else:
                status_items.append(("Synced tabs", "○", "No synced devices"))
        except Exception as e:
            status_items.append(("Synced tabs", "✗", str(e)))

        for name, symbol, detail in status_items:
            click.echo(f"  {symbol} {name:<15} {detail}")

        click.echo()
    finally:
        reader.close()


if __name__ == "__main__":
    cli()
