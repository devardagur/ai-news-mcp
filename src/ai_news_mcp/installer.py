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


def load_fetch_job() -> None:
    """Register the job with launchd. An older copy is removed first, so running install again is safe."""
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{JOB_LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(JOB_PLIST)], check=True)


def run() -> None:
    add_to_claude_desktop()
    print(f"Added to Claude Desktop: {CLAUDE_CONFIG}")

    write_fetch_job()
    load_fetch_job()
    print(f"Daily fetch scheduled at 09:00: {JOB_PLIST}")

    print("Running the first fetch...")
    fetcher.run()

    print("Done. Restart Claude Desktop to start using ai-news.")
