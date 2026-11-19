"""Install: add the server to Claude Desktop, schedule the daily fetch with launchd, and run the first fetch.
Uninstall: undo all of that and delete the stored data."""

import json
import os
import plistlib
import shutil
import subprocess
from pathlib import Path

from ai_news_mcp import db, fetcher

CLAUDE_CONFIG = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
JOB_LABEL = "com.ai-news-mcp.fetch"
JOB_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{JOB_LABEL}.plist"
LOG_PATH = db.DB_PATH.parent / "fetch.log"
# Claude Desktop writes this log for each MCP server it runs.
CLAUDE_LOG = Path.home() / "Library" / "Logs" / "Claude" / "mcp-server-ai-news.log"
# Root of the cloned repo (this file is src/ai_news_mcp/installer.py).
PROJECT_DIR = Path(__file__).resolve().parents[2]

# First try at 09:00, then once an hour until 23:00. The fetch itself skips if today already succeeded,
# so these extra runs only matter when the 09:00 run failed or the Mac was off.
FETCH_HOURS = range(9, 24)


def _command(subcommand: str) -> list[str]:
    """Command that runs `ai-news-mcp <subcommand>` from the cloned repo, for Claude Desktop and launchd."""
    if not (PROJECT_DIR / "pyproject.toml").exists():
        raise SystemExit("Run install from the cloned repo: uv run ai-news-mcp install")
    # Claude Desktop and launchd start programs with a minimal PATH, so the full path to uv is needed.
    # `uv run` sets UV to its own path; the PATH lookup covers running the script directly.
    uv = os.environ.get("UV") or shutil.which("uv")
    if uv is None:
        raise SystemExit("uv was not found. Install uv first: https://docs.astral.sh/uv/")
    return [uv, "run", "--directory", str(PROJECT_DIR), "ai-news-mcp", subcommand]


def add_to_claude_desktop() -> None:
    """Add or update the "ai-news" entry in Claude Desktop's config, keeping all other settings."""
    command, *args = _command("serve")
    config = json.loads(CLAUDE_CONFIG.read_text()) if CLAUDE_CONFIG.exists() else {}
    config.setdefault("mcpServers", {})["ai-news"] = {"command": command, "args": args}
    CLAUDE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_CONFIG.write_text(json.dumps(config, indent=2) + "\n")


def write_fetch_job() -> None:
    """Write the launchd job file that runs `ai-news-mcp fetch` on schedule."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    JOB_PLIST.parent.mkdir(parents=True, exist_ok=True)
    job = {
        "Label": JOB_LABEL,
        "ProgramArguments": _command("fetch"),
        "StartCalendarInterval": [{"Hour": hour, "Minute": 0} for hour in FETCH_HOURS],
        # Output goes to a log file, so a failed fetch can be checked later.
        "StandardOutPath": str(LOG_PATH),
        "StandardErrorPath": str(LOG_PATH),
    }
    JOB_PLIST.write_bytes(plistlib.dumps(job))


def unload_fetch_job() -> None:
    """Remove the job from launchd. Fails quietly if it is not loaded."""
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{JOB_LABEL}"], capture_output=True)


def load_fetch_job() -> None:
    """Register the job with launchd. An older copy is removed first, so running install again is safe."""
    unload_fetch_job()
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(JOB_PLIST)], check=True)


def remove_from_claude_desktop() -> None:
    """Remove the "ai-news" entry from Claude Desktop's config, keeping all other settings."""
    if not CLAUDE_CONFIG.exists():
        return
    config = json.loads(CLAUDE_CONFIG.read_text())
    servers = config.get("mcpServers", {})
    servers.pop("ai-news", None)
    # Drop the section if nothing else is in it, so the config looks as it did before install.
    if not servers:
        config.pop("mcpServers", None)
    CLAUDE_CONFIG.write_text(json.dumps(config, indent=2) + "\n")


def run() -> None:
    add_to_claude_desktop()
    print(f"Added to Claude Desktop: {CLAUDE_CONFIG}")

    write_fetch_job()
    load_fetch_job()
    print(f"Daily fetch scheduled at 09:00: {JOB_PLIST}")

    print("Running the first fetch...")
    fetcher.run()

    print("Done. Restart Claude Desktop to start using ai-news.")


def uninstall() -> None:
    """Undo install: remove the Claude Desktop entry and the daily job, and delete all stored data and logs."""
    # A running server could recreate the database, and Claude Desktop could rewrite its log, after we delete them.
    if subprocess.run(["pgrep", "-f", "ai-news-mcp serve"], capture_output=True).returncode == 0:
        raise SystemExit(
            "Claude Desktop is still running the ai-news server.\n"
            "Quit Claude Desktop (Cmd+Q), then run uninstall again."
        )

    remove_from_claude_desktop()
    print(f"Removed from Claude Desktop: {CLAUDE_CONFIG}")

    unload_fetch_job()
    JOB_PLIST.unlink(missing_ok=True)
    print(f"Removed the daily fetch job: {JOB_PLIST}")

    shutil.rmtree(db.DB_PATH.parent, ignore_errors=True)
    CLAUDE_LOG.unlink(missing_ok=True)
    print(f"Deleted the database and logs: {db.DB_PATH.parent}")

    print("Done. You can now delete this cloned folder.")
