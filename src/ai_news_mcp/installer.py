"""One-time setup: add the server to Claude Desktop, schedule the daily fetch with launchd, and run the first fetch."""

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

# First try at 09:00, then once an hour until 23:00. The fetch itself skips if today already succeeded,
# so these extra runs only matter when the 09:00 run failed or the Mac was off.
FETCH_HOURS = range(9, 24)


def _uvx_path() -> str:
    # Claude Desktop and launchd start programs with a minimal PATH, so the full path to uvx is needed.
    path = shutil.which("uvx")
    if path is None:
        raise SystemExit("uvx was not found. Install uv first: https://docs.astral.sh/uv/")
    return path


def add_to_claude_desktop(uvx: str) -> None:
    """Add or update the "ai-news" entry in Claude Desktop's config, keeping all other settings."""
    config = json.loads(CLAUDE_CONFIG.read_text()) if CLAUDE_CONFIG.exists() else {}
    config.setdefault("mcpServers", {})["ai-news"] = {"command": uvx, "args": ["ai-news-mcp", "serve"]}
    CLAUDE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_CONFIG.write_text(json.dumps(config, indent=2) + "\n")


def write_fetch_job(uvx: str) -> None:
    """Write the launchd job file that runs `ai-news-mcp fetch` on schedule."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    JOB_PLIST.parent.mkdir(parents=True, exist_ok=True)
    job = {
        "Label": JOB_LABEL,
        "ProgramArguments": [uvx, "ai-news-mcp", "fetch"],
        "StartCalendarInterval": [{"Hour": hour, "Minute": 0} for hour in FETCH_HOURS],
        # Output goes to a log file, so a failed fetch can be checked later.
        "StandardOutPath": str(LOG_PATH),
        "StandardErrorPath": str(LOG_PATH),
    }
    JOB_PLIST.write_bytes(plistlib.dumps(job))


def load_fetch_job() -> None:
    """Register the job with launchd. An older copy is removed first, so running install again is safe."""
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{JOB_LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(JOB_PLIST)], check=True)


def run() -> None:
    uvx = _uvx_path()

    add_to_claude_desktop(uvx)
    print(f"Added to Claude Desktop: {CLAUDE_CONFIG}")

    write_fetch_job(uvx)
    load_fetch_job()
    print(f"Daily fetch scheduled at 09:00: {JOB_PLIST}")

    print("Running the first fetch...")
    fetcher.run()

    print("Done. Restart Claude Desktop to start using ai-news.")
